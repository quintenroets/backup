from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from backup.models import BackupConfig, PathRule
from backup.path import Path
from backup.syncer import SyncConfig

from .entry import Entry


@dataclass
class CacheScanner:
    backup_config: BackupConfig
    visited: set[Path] = field(default_factory=set)

    def generate_entries(self) -> Iterator[Entry]:
        for rule in self.generate_rules():
            source_path = self.backup_config.source / rule.path
            dest_path = self.backup_config.cache / rule.path
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
        sync_config = SyncConfig(self.backup_config.source, self.backup_config.cache)
        if sync_config.overlapping_sub_path is not None:
            yield PathRule(Path(sync_config.overlapping_sub_path), include=False)
        yield from self.backup_config.rules

    def create_entry(self, **kwargs: Any) -> Entry:
        return Entry(self.backup_config, **kwargs)

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or self.backup_config.ignores.matches(path)
            or path.is_symlink()
        )
