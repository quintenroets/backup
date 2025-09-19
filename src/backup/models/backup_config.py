from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, TypeVar

from package_utils.dataclasses.mixins import SerializationMixin

from .path import Path

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class PathRule:
    path: Path
    include: bool


@dataclass
class SerializedEntryConfig(SerializationMixin):
    source: str = ""
    dest: str = ""
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class SerializedBackupConfig(SerializationMixin):
    syncs: list[SerializedEntryConfig]
    source: str = "/"
    dest: str = "/"
    cache: str = str(Path.backup_cache)


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    cache: Path
    rules: list[PathRule] = field(default_factory=list)
