import fnmatch
import re
from dataclasses import dataclass, field
from functools import cached_property

from backup.syncer import FileState, PathRule, resolve_rules

from .path import Path, create_prefix, generate_ancestors

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

    rules: list[PathRule] = field(default_factory=list)
    ignores: Ignores = field(default_factory=Ignores)
    sub_path: Path = field(default_factory=Path)
    max_backup_size: int = default_max_backup_size

    def includes(self, relative: str) -> bool:
        """Whether the rules cover a path that no walk pruned."""
        matching = (
            self.decisions[ancestor]
            for ancestor in generate_ancestors(relative)
            if ancestor in self.decisions
        )
        return next(matching, self.root_decision)

    def covers_child(self, relative: str, *, name: str) -> bool:
        """Whether a path stays in scope, given a walk already covered its parent."""
        included = self.decisions.get(relative, True)
        return included and not self.ignored_directly(relative, name=name)

    def ignored(self, relative: str) -> bool:
        """Whether the ignores name this path or any of its ancestors."""
        return any(
            self.ignored_directly(ancestor, name=ancestor.rsplit("/", 1)[-1])
            for ancestor in generate_ancestors(relative)
        )

    def ignored_directly(self, relative: str, *, name: str) -> bool:
        """Whether the ignores name this path itself, ancestors left to the caller."""
        return self.ignores.matches(f"{self.ignore_prefix}{relative}", name=name)

    def exceeds_size_limit(self, relative: str, state: FileState) -> bool:
        return state.size > self.max_backup_size and not relative.endswith(".zip")

    @cached_property
    def deepest_first(self) -> list[PathRule]:
        return resolve_rules(self.rules)

    @cached_property
    def decisions(self) -> dict[str, bool]:
        rules = self.deepest_first
        return {str(rule.path): rule.include for rule in rules if rule.depth}

    @cached_property
    def root_decision(self) -> bool:
        return any(rule.include for rule in self.deepest_first if not rule.depth)

    @cached_property
    def ignore_prefix(self) -> str:
        return create_prefix(self.sub_path)
