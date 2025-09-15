import fnmatch
from itertools import groupby
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import cli

from backup import backup
from backup.context import context
from backup.models import Changes, Path
from backup.utils import parser
from backup.utils.parser import PathRule

from .detailed_entry import Entry
from typing import Any, Iterator


@dataclass
class Backup(backup.Backup):
    dest: Path = field(default_factory=context.extract_cache_path)
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    number_of_entries: int = 0
    rules: list[PathRule] = field(default_factory=list)
    entries: set[Entry] = field(default_factory=set)

    def status(self, *, reverse: bool = False) -> Changes:
        self.paths = list(self.generate_changed_paths())
        return super().capture_status(reverse=reverse) if self.paths else Changes()

    def generate_changed_paths(self) -> Iterator[Path]:
        for entry in self.entries:
            if entry.is_changed():
                yield from entry.get_paths()

    def generate_entries(self) -> Iterator[Entry]:
        yield from self.generate_source_entries()
        # yield from self.generate_dest_entries()

    def generate_source_entries(self) -> Iterator[Entry]:
        rules = self.entry_rules()
        for rule in rules:
            path = self.source / rule.path
            if rule.include:
                for source_path in path.find(exclude=self.exclude_root):
                    yield self.create_entry(source=source_path)
            self.visited.add(path)

    def generate_dest_entries(self) -> Iterator[Entry]:
        print(self.dest)
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
        # include everything else if no include rules
        yield parser.PathRule(Path(), include=not any_include)

    def generate_entry_rules(self) -> Iterator[parser.PathRule]:
        self.check_config_path()
        if self.overlapping_sub_path is not None:
            path = context.config.cache_path.relative_to(self.source)
            self.rules.insert(0, parser.PathRule(path, include=False))
        if self.sub_check_path is not None:
            relative_source = self.source.relative_to(Path(""))
            for rule in self.rules:
                if rule.path.is_relative_to(relative_source):
                    rule.path = rule.path.relative_to(relative_source)
                    yield rule
        else:
            yield from self.rules

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
