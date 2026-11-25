from __future__ import annotations

import fnmatch
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated, Any

from package_utils.dataclasses.mixins import SerializationMixin
from superpathlib import Path

if TYPE_CHECKING:
    import typer

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
class RcloneConfig:
    update: bool = False
    retries: int = 5
    retries_sleep: str = "30s"
    checkers: int = 100
    transfers: int = 100
    order_by: str = "size,desc"
    drive_import_formats: str = "docx, xlsx"


@dataclass
class Config(SerializationMixin):
    source: Path
    dest: Path
    syncs: list[SyncEntry]
    cache: Path = assets_directory / "cache"
    ignores: Ignores = field(default_factory=Ignores)
    max_backup_size: int = int(50e6)
    rclone: RcloneConfig = field(default_factory=RcloneConfig)


@dataclass
class Backup:
    source: Path
    dest: Path
    cache: Path
    rules: list[PathRule]
    config: Config


Plan = tuple[Backup, dict[Path, str]]


class Action(StrEnum):
    push = "push"
    pull = "pull"


class Help:
    action: str = "The action to do"
    confirm_push: str = "Ask confirmation before pushing"
    sub_check: str = "only check subpath of current working directory"
    cache_only: str = "pull from local cache without syncing from remote"


@dataclass
class Options:
    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.push
    confirm_push: Annotated[bool, typer.Option(help=Help.confirm_push)] = True
    sub_check: Annotated[bool, typer.Option(help=Help.sub_check)] = False
    cache_only: Annotated[bool, typer.Option(help=Help.cache_only)] = False
