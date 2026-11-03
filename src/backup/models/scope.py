import fnmatch
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property

from backup.syncer import FileState, PathRule

default_max_backup_size = int(50e6)


@dataclass
class Ignores:
    names: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)

    @cached_property
    def ignored_names(self) -> set[str]:
        return set(self.names)

    @cached_property
    def pattern(self) -> re.Pattern[str]:
        never_matches = "(?!)"
        translated = [fnmatch.translate(pattern) for pattern in self.patterns]
        return re.compile("|".join(translated) or never_matches)

    def matches(self, relative: str, *, name: str) -> bool:
        return name in self.ignored_names or self.pattern.match(relative) is not None


@dataclass
class Scope:
    """Whether a path is covered by a config, in either direction."""

    rules: list[PathRule]
    ignores: Ignores = field(default_factory=Ignores)
    max_backup_size: int = default_max_backup_size

    def includes(self, relative: str) -> bool:
        """Whether the rules cover a path that no walk pruned."""
        matching = (
            self.decisions[ancestor]
            for ancestor in generate_ancestors(relative)
            if ancestor in self.decisions
        )
        return next(matching, self.root_decision)

    def continues_walk(self, relative: str, *, name: str) -> bool:
        """Whether a walk enters a child, which its own rule walks if it has one."""
        decided = relative in self.decisions
        return not decided and not self.ignores.matches(relative, name=name)

    def ignored(self, relative: str) -> bool:
        """Whether an ignore names this path or an ancestor up to its deepest rule."""
        return any(
            self.ignores.matches(ancestor, name=ancestor.rsplit("/", 1)[-1])
            for ancestor in self.generate_governed_ancestors(relative)
        )

    def generate_governed_ancestors(self, relative: str) -> Iterator[str]:
        governed = True
        for ancestor in generate_ancestors(relative):
            if governed:
                yield ancestor
            governed = governed and ancestor not in self.decisions

    def exceeds_size_limit(self, relative: str, state: FileState) -> bool:
        return state.size > self.max_backup_size and not relative.endswith(".zip")

    @cached_property
    def deepest_first(self) -> list[PathRule]:
        ordered = sorted(self.rules, key=lambda rule: (-rule.depth, rule.include))
        return list({rule.path: rule for rule in ordered}.values())

    @cached_property
    def decisions(self) -> dict[str, bool]:
        rules = self.deepest_first
        return {str(rule.path): rule.include for rule in rules if rule.depth}

    @cached_property
    def root_decision(self) -> bool:
        return any(rule.include for rule in self.deepest_first if not rule.depth)


def generate_ancestors(relative: str) -> Iterator[str]:
    yield relative
    while "/" in relative:
        relative = relative.rsplit("/", 1)[0]
        yield relative
