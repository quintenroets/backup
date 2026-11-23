from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from package_utils.context import Context

from .models import assets_directory

if TYPE_CHECKING:
    import typer
    from superpathlib import Path


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
    config_path: Path = assets_directory / "config"


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
class Config:
    max_backup_size: int = int(50e6)
    rclone: RcloneConfig = field(default_factory=RcloneConfig)


context: Context[Options, Config, None] = Context(Options, Config)
