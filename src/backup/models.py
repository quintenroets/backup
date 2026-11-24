from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from package_utils.dataclasses.mixins import SerializationMixin
from superpathlib import Path

assets_directory = Path.script_assets / "backup"

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
    path: Path
    include: bool


@dataclass
class SyncEntry:
    source: Path = field(default_factory=Path)
    dest: Path = field(default_factory=Path)
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


@dataclass
class Config(SerializationMixin):
    source: Path
    dest: Path
    syncs: list[SyncEntry]
    cache: Path = assets_directory / "cache"
    ignores: Ignores = field(default_factory=Ignores)


@dataclass
class Backup:
    source: Path
    dest: Path
    cache: Path
    rules: list[PathRule]
    ignores: Ignores


@dataclass(frozen=True)
class Change:
    path: Path
    type: ChangeType


Plan = tuple[Backup, list[Change]]


class ChangeType(StrEnum):
    created = "+"
    modified = "*"
    deleted = "-"
    preserved = "="
