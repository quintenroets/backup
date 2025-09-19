from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import Any

import cli

from backup.context import context
from backup.models import BackupConfig, Changes, Path
from backup.syncer import SyncConfig, Syncer
from backup.utils import exporter
from backup.utils.parser.config import parse_config

from .cache.cache_syncer import CacheSyncer
from .change_scanner import ChangeScanner


@dataclass
class Backup:
    config: dict[str, Any]

    @cached_property
    def backup_configs(self) -> list[BackupConfig]:
        return list(parse_config(self.config))

    def status(self) -> None:
        changes = ChangeScanner(self.backup_configs).calculate_changes()
        statuses = [
            Syncer(config).capture_status()
            for config in self.generate_sync_configs(changes)
        ]
        for status in statuses:
            status.print()

    def push(self, *, reverse: bool = False) -> list[Changes]:
        changes = ChangeScanner(self.backup_configs).check_changes(reverse=reverse)
        cache_configs = self.generate_sync_configs(changes)
        remote_configs = self.generate_sync_configs(changes, cache=False)
        for cache, remote in zip(cache_configs, remote_configs, strict=False):
            Syncer(remote).push(reverse=reverse)
            Syncer(cache).push()
        return changes

    def pull(self) -> None:
        if not context.options.no_sync:
            self.sync_remote_changes()
        changes = self.push(reverse=True)
        should_upload_resume = (
            changes
            and any(changes)
            and self.contains_change(Path.resume, changes)
            and exporter.export_resume()
        )
        if should_upload_resume:
            config = SyncConfig(path=Path.main_resume_pdf)
            with cli.status("Uploading new resume pdf"):
                Syncer(config).capture_push()

    def contains_change(self, path: Path, changes: list[Changes]) -> bool:
        changed = False
        for change, config in zip(changes, self.backup_configs, strict=False):
            if path.is_relative_to(config.source):
                relative_path = path.relative_to(config.source)
                changed |= any(
                    item.path.is_relative_to(relative_path) for item in change
                )
        return changed

    def sync_remote_changes(self) -> None:
        for item in self.backup_configs:
            CacheSyncer(item).sync_remote_changes()

    def generate_sync_configs(
        self,
        changes: Iterable[Changes],
        *,
        cache: bool = True,
    ) -> Iterator[SyncConfig]:
        for item, change in zip(self.backup_configs, changes, strict=False):
            if change.paths:
                yield SyncConfig(
                    source=item.source,
                    dest=item.cache if cache else item.dest,
                    paths=change.paths,
                )
