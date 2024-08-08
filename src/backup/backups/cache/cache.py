import fnmatch
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import cli

from backup import backup
from backup.context import context
from backup.models import Changes, Path
from backup.utils import parser

from .detailed_entry import Entry


@dataclass
class Backup(backup.Backup):
    dest: Path = field(default_factory=context.extract_cache_path)
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    number_of_entries: int = 0

    def status(self, *, reverse: bool = False) -> Changes:
        self.paths = list(self.generate_changed_paths())
        return super().capture_status(reverse=reverse) if self.paths else Changes([])

    def generate_changed_paths(self) -> Iterator[Path]:
        entries: Iterable[Entry] = self.generate_entries()
        total = context.storage.number_of_paths
        entries = cli.track_progress(
            entries,
            description="Checking",
            unit="Files",
            total=total,
            cleanup_after_finish=True,
        )

        path_entries = set(entries)
        for entry in path_entries:
            if entry.is_changed():
                yield from entry.get_paths()

    def generate_entries(self) -> Iterator[Entry]:
        for path in self.generate_path_entries():
            yield path
            self.number_of_entries += 1
        context.storage.number_of_paths = self.number_of_entries

    def generate_path_entries(self) -> Iterator[Entry]:
        yield from self.generate_source_entries()
        yield from self.generate_dest_entries()

    def generate_source_entries(self) -> Iterator[Entry]:
        rules = self.entry_rules()
        for rule in rules:
            path = self.source / rule.path
            if rule.include:
                for source_path in path.find(exclude=self.exclude_root):
                    yield self.create_entry(source=source_path)
            self.visited.add(path)

    def generate_dest_entries(self) -> Iterator[Entry]:
        for dest_path in self.dest.rglob("*"):
            yield self.create_entry(dest=dest_path)

    def create_entry(self, **kwargs: Any) -> Entry:
        return Entry(self.source, self.dest, **kwargs)

    def entry_rules(self) -> Iterator[parser.PathRule]:
        any_include = False
        rules = self.generate_entry_rules()
        for rule in rules:
            any_include |= rule.include
            yield rule
        if not any_include:
            # include everything else if no include rules
            root = Path()
            yield parser.PathRule(root, include=True)

    def generate_entry_rules(self) -> Iterator[parser.PathRule]:
        self.check_config_path()
        root = context.config.backup_source
        rules = list(
            parser.Rules(self.include_dict, context.storage.excludes, root=root),
        )
        if self.overlapping_sub_path is not None:
            path = context.config.cache_path.relative_to(root)
            rules.insert(0, parser.PathRule(path, include=False))
        if self.sub_check_path is not None:
            relative_source = self.source.relative_to(root)
            for rule in rules:
                if rule.path.is_relative_to(relative_source):
                    rule.path = rule.path.relative_to(relative_source)
                    yield rule
        else:
            yield from rules

    @classmethod
    def check_config_path(cls) -> None:
        if not Path.config.exists():
            backup.Backup(directory=Path.config).capture_pull()

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or any(
                fnmatch.fnmatch(str(path), pattern) for pattern in self.ignore_patterns
            )
            or path.name in context.storage.ignore_names
            or path.is_symlink()
        )

    @cached_property
    def ignore_patterns(self) -> list[str]:
        ignore_patterns = context.storage.ignore_patterns
        if not context.options.include_browser:
            ignore_patterns.append(context.config.browser_pattern)
        return ignore_patterns

    @cached_property
    def include_dict(self) -> list[str | dict[str, Any]]:
        includes = context.storage.includes
        if not context.options.include_browser:
            self.remove_browser(includes)
        return includes

    @classmethod
    def remove_browser(cls, includes: list[str | dict[str, Any]]) -> None:
        for include in includes:
            if isinstance(include, dict):
                key, value = next(iter(include.items()))
                cls.remove_browser(value)
                if context.config.browser_name in key:
                    includes.remove(include)
