from dataclasses import dataclass, field
from typing import Any

from package_utils.dataclasses.mixins import SerializationMixin

from backup.syncer import RcloneConfig, SyncConfig, Syncer

from .path import Path
from .scope import Ignores, Scope, default_max_backup_size
from .sync_state import SyncRecords

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class SerializedEntryConfig(SerializationMixin):
    source: str = ""
    dest: str = ""
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class Config(SerializationMixin):
    syncs: list[SerializedEntryConfig]
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
    sync_state: SyncRecords
    scope: Scope = field(default_factory=Scope)
    rclone: RcloneConfig = field(default_factory=RcloneConfig)

    def create_syncer(self, config: SyncConfig | None = None) -> Syncer:
        return Syncer(self.sync_config if config is None else config, self.rclone)

    @property
    def sync_config(self) -> SyncConfig:
        return SyncConfig(self.source, self.dest, rules=self.scope.deepest_first)
