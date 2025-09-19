from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime

import cli

from backup.context import context
from backup.models import Path, BackupConfig
from backup.syncer import SyncConfig, Syncer

from .cache_scanner import CacheScanner


@dataclass
class CacheSyncer:
    backup_config: BackupConfig
    date_start: str = "── ["
    date_end: str = "]  /"

    def sync_remote_changes(self) -> None:
        path = self.backup_config.source.resolve().short_notation
        with cli.status(f"Reading remote filesystem at {path}"):
            self.run_remote_sync()

    def run_remote_sync(self) -> None:
        filter_rules = list(self.generate_pull_filters())
        config = SyncConfig(
            self.backup_config.cache, self.backup_config.dest, filter_rules=filter_rules
        )
        remote_pairs = Syncer(config).generate_paths_with_time()
        remote_pairs = self.modify_changed_paths(remote_pairs)
        remote_paths = {path for path, _ in remote_pairs}
        self.remove_paths_missing_in_remote(remote_paths, config)

    def modify_changed_paths(
        self,
        pairs: Iterator[tuple[Path, datetime]],
    ) -> Iterator[tuple[Path, datetime]]:
        for path, date in pairs:
            cache_path = self.backup_config.source / path
            changed = not cache_path.exists() or not cache_path.has_date(date)
            if changed:
                changed = not cache_path.has_date(date, check_tag=True)
            if changed:
                self.change_path(path)
            yield path, date

    def change_path(self, path: Path) -> None:
        # change content and mtime trigger update
        cache_path = self.backup_config.source / path
        path.text = "" if cache_path.size else " "
        path.touch(mtime=path.mtime + 1)

    def remove_paths_missing_in_remote(
        self,
        remote_paths: set[Path],
        config: SyncConfig,
    ) -> None:
        pairs = Syncer(config).generate_paths_with_time(config.source)
        for path, _ in pairs:
            if path not in remote_paths:
                (self.backup_config.source / path).unlink()

    def generate_pull_filters(self) -> Iterator[str]:
        rules = CacheScanner(self.backup_config).generate_rules()
        for rule in rules:
            sign = "+" if rule.include else "-"
            pattern = f"{sign} /{rule.path}"
            yield pattern
            yield f"{pattern}/**"
