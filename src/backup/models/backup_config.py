from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from package_utils.dataclasses.mixins import SerializationMixin

from backup.syncer import FileState, PathRule, RcloneConfig, Snapshot, Syncer

from .change import Action
from .path import Path
from .scope import Ignores, Scope, default_max_backup_size
from .sync_state import SyncRecords

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class SyncEntry(SerializationMixin):
    source: str = ""
    dest: str = ""
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class Config(SerializationMixin):
    syncs: list[SyncEntry]
    source: str = "/"
    dest: str = "/"
    sync_state: str = str(Path.sync_state)
    ignores: Ignores = field(default_factory=Ignores)
    max_backup_size: int = default_max_backup_size
    rclone: RcloneConfig = field(default_factory=RcloneConfig)


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    records: SyncRecords
    scope: Scope
    rclone: RcloneConfig

    def create_syncer(self, paths: list[str], action: Action = Action.push) -> Syncer:
        rules = PathRule.select(paths)
        syncer = Syncer(self.source, self.dest, rules, self.rclone)
        return syncer.reversed if action == Action.pull else syncer

    def list_remote(self) -> Snapshot:
        rules = self.scope.deepest_first
        return Syncer(self.source, self.dest, rules, self.rclone).list_remote_files()

    def observe_local(self, paths: Iterable[str]) -> Snapshot:
        states = {path: FileState.observe(self.source / path) for path in paths}
        return {path: state for path, state in states.items() if state is not None}
