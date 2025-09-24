import fnmatch
from collections.abc import Iterator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

from backup.context import context
from backup.models import BackupConfig, Changes, Path, PathRule
from backup.syncer import SyncConfig, Syncer

from .entry import Entry


@dataclass
class CacheScanner:
    backup_config: BackupConfig
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    entries: set[Entry] = field(default_factory=set)

    @property
    def sync_config(self) -> SyncConfig:
        return SyncConfig(
            source=self.backup_config.source,
            dest=self.backup_config.cache,
        )

    def calculate_changes(self, *, reverse: bool = False) -> Changes:
        paths = [
            path
            for entry in self.entries
            for path in entry.get_paths()
            if entry.is_changed()
        ]
        return (
            Syncer(self.sync_config.with_paths(paths)).capture_status(
                reverse=reverse,
                is_cache=True,
            )
            if paths
            else Changes()
        )

    def generate_entries(self) -> Iterator[Entry]:
        for rule in self.generate_rules():
            source_path = self.sync_config.source / rule.path
            dest_path = self.sync_config.dest / rule.path
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

    def generate_rules(self) -> Iterator[PathRule]:
        if self.sync_config.overlapping_sub_path is not None:
            yield PathRule(self.sync_config.overlapping_sub_path, include=False)
        yield from self.backup_config.rules

    def create_entry(self, **kwargs: Any) -> Entry:
        return Entry(self.backup_config, **kwargs)

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
