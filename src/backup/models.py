from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any

from package_utils.dataclasses.mixins import SerializationMixin

from .path import Path

if TYPE_CHECKING:
    import superpathlib

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class Ignores:
    names: list[str] = field(default_factory=list)
    patterns: list[str] = field(default_factory=list)

    def matches(self, path: Path) -> bool:
        return path.name in self.names or any(
            fnmatch.fnmatch(str(path), pattern) for pattern in self.patterns
        )


@dataclass
class PathRule:
    path: superpathlib.Path
    include: bool


@dataclass
class SerializedEntryConfig(SerializationMixin):
    source: Path = field(default_factory=Path)
    dest: Path = field(default_factory=Path)
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class SerializedBackupConfig(SerializationMixin):
    syncs: list[SerializedEntryConfig]
    dest: Path
    source: Path = Path.backup_source
    cache: Path = Path.assets / "cache"
    ignores: Ignores = field(default_factory=Ignores)


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    cache: Path
    rules: list[PathRule]
    ignores: Ignores


@dataclass(frozen=True)
class Change:
    path: superpathlib.Path
    type: ChangeType


Changes = list[Change]
Plan = tuple[BackupConfig, Changes]


class ChangeType(StrEnum):
    created = "+"
    modified = "*"
    deleted = "-"
    preserved = "="
