from backup.models import Path

from dataclasses import dataclass, field
from typing import Any

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class BackupConfigs:
    backups: list[BackupConfig]
