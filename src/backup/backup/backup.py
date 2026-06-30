from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from functools import cached_property
from typing import Any

from backup.context import Action, context
from backup.models import BackupConfig, Changes
from backup.syncer import SyncConfig, Syncer
from backup.utils.parser.config import parse_config

from .cache import CacheSyncer
from .change_scanner import ChangeScanner


def run(config: dict[str, Any]) -> list[Changes]:
    backup = Backup(config)
    return backup.pull() if context.options.action == Action.pull else backup.push()


@dataclass
class Backup:
    config: dict[str, Any]

    @cached_property
    def backup_configs(self) -> list[BackupConfig]:
        return list(parse_config(self.config))

    def push(self, *, reverse: bool = False) -> list[Changes]:
        changes = ChangeScanner(self.backup_configs).check_changes(reverse=reverse)
        cache_configs = self.generate_sync_configs(changes)
        remote_configs = self.generate_sync_configs(changes, cache=False)
        for cache, remote in zip(cache_configs, remote_configs, strict=False):
            Syncer(remote).push(reverse=reverse)
            Syncer(cache).push()
        return changes

    def pull(self) -> list[Changes]:
        if not context.options.cache_only:
            for item in self.backup_configs:
                CacheSyncer(item).sync_from_remote()
        return self.push(reverse=True)

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
