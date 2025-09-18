import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from backup.backup.config import BackupConfig
from backup.context import context
from backup.models import Changes, Path
from backup.syncer import SyncConfig, Syncer
from backup.utils import parser
from backup.utils.parser import Rules

from .entry import Entry


@dataclass
class CacheScanner:
    backup_config: BackupConfig
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    entries: set[Entry] = field(default_factory=set)

    @property
    def config(self) -> SyncConfig:
        return SyncConfig(
            source=self.backup_config.source, dest=self.backup_config.cache
        )

    def calculate_changes(self, *, reverse: bool = False) -> Changes:
        paths = [
            path
            for entry in self.entries
            for path in entry.get_paths()
            if entry.is_changed()
        ]
        return (
            Syncer(self.config.with_paths(paths)).capture_status(
                reverse=reverse, is_cache=True
            )
            if paths
            else Changes()
        )

    def generate_entries(self) -> Iterator[Entry]:
        rules = self.generate_entry_rules()
        for rule in rules:
            source_path = self.config.source / rule.path
            dest_path = self.config.dest / rule.path
            if rule.include:
                is_file = source_path.is_file() or dest_path.is_file()
                if is_file:
                    if source_path.exists():
                        yield self.create_entry(source=source_path)
                    else:
                        yield self.create_entry(dest=dest_path)
                else:
                    for entry_path in source_path.find(exclude=self.exclude_root):
                        yield self.create_entry(source=entry_path)
                    for entry_path in dest_path.find(
                        exclude=lambda path_: path_ in self.visited,
                    ):
                        yield self.create_entry(dest=entry_path)
            self.visited.add(source_path)
            self.visited.add(dest_path)

    def create_entry(self, **kwargs: Any) -> Entry:
        return Entry(self.backup_config, **kwargs)

    def generate_entry_rules(self) -> Iterator[parser.PathRule]:
        rules = Rules(
            self.backup_config.includes,
            self.backup_config.excludes,
            self.backup_config.source,
        )
        if self.config.overlapping_sub_path is not None:
            yield parser.PathRule(self.config.overlapping_sub_path, include=False)
        yield from rules.rules
        yield parser.PathRule(Path(), include=False)

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
