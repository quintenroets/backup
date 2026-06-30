import fnmatch
from dataclasses import dataclass, field
from typing import Any

from package_utils.dataclasses.mixins import SerializationMixin

from .path import Path

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
    ignores: Ignores = field(default_factory=Ignores)


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    cache: Path
    rules: list[PathRule] = field(default_factory=list)
    ignores: Ignores = field(default_factory=Ignores)
