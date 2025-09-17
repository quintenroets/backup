from .change_scanner import ChangeScanner
from .cache_syncer import CacheSyncer
from typing import Iterable
from functools import cached_property
from collections.abc import Iterator
from dataclasses import dataclass

import cli

from backup.context import context
from backup.models import Changes, Path, BackupConfigs
from backup.rclone import RcloneConfig, Rclone
from backup.utils import exporter


from .config import load_config


@dataclass
class Backup:
    def status(self) -> None:
        changes = ChangeScanner(self.backup_configs).calculate_changes()
        statuses = [
            Rclone(config).capture_status()
            for config in self.generate_rclone_configs(changes)
        ]
        for status in statuses:
            status.print()

    def push(self, *, reverse: bool = False) -> list[Changes]:
        changes = ChangeScanner(self.backup_configs).check_changes(reverse=reverse)
        dest = context.extract_backup_dest()
        cache_ = context.extract_cache_path()
        for config in self.generate_rclone_configs(changes):
            Rclone(config.with_dest_root(dest)).push(reverse=reverse)
            Rclone(config.with_dest_root(cache_)).push()
        return changes

    def pull(self) -> None:
        if not context.options.no_sync:
            self.sync_remote_changes()
        changes = self.push(reverse=True)
        if changes and any(changes):
            if self.contains_change(Path.resume, changes) and exporter.export_resume():
                config = RcloneConfig(path=Path.main_resume_pdf)
                with cli.status("Uploading new resume pdf"):
                    Rclone(config).capture_push()

    def contains_change(self, path: Path, changes: list[Changes]) -> bool:
        changed = False
        for change, config in zip(changes, self.backup_configs.backups):
            if path.is_relative_to(config.source):
                relative_path = path.relative_to(config.source)
                changed |= any(
                    item.path.is_relative_to(relative_path) for item in change
                )
        return changed

    def sync_remote_changes(self) -> None:
        for item in self.backup_configs.backups:
            CacheSyncer(item).sync_remote_changes()

    @cached_property
    def backup_configs(self) -> BackupConfigs:
        if not Path.config.exists():
            Rclone(RcloneConfig(directory=Path.config)).capture_pull()
        return BackupConfigs(backups=list(load_config()))

    def generate_rclone_configs(
        self, changes: Iterable[Changes]
    ) -> Iterator[RcloneConfig]:
        for item, change in zip(self.backup_configs.backups, changes):
            if change.paths:
                yield RcloneConfig(
                    source=item.source,
                    dest=item.dest,
                    paths=change.paths,
                )
