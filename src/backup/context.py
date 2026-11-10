from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import StrEnum
from functools import cached_property
from typing import TYPE_CHECKING, Annotated

import cli
from package_utils.context import Context as Context_
from package_utils.secrets_ import load_secret

from .path import Path

if TYPE_CHECKING:
    import typer


class Action(StrEnum):
    push = "push"
    pull = "pull"


class Help:
    action: str = "The action to do"
    configure: str = "Open configuration"
    confirm_push: str = "Ask confirmation before pushing"
    sub_check: str = "only check subpath of current working directory"
    cache_only: str = "pull from local cache without syncing from remote"


@dataclass
class Options:
    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.push
    configure: Annotated[bool, typer.Option(help=Help.configure)] = False
    confirm_push: Annotated[bool, typer.Option(help=Help.confirm_push)] = True
    sub_check: Annotated[bool, typer.Option(help=Help.sub_check)] = False
    cache_only: Annotated[bool, typer.Option(help=Help.cache_only)] = False
    config_path: Path = Path.assets / "config"


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


class Context(Context_[Options, Config, None]):
    @cached_property
    def rclone_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
            env["RCLONE_CONFIG_PASS"] = load_secret("rclone")
        return env

    @cached_property
    def remote(self) -> str:
        return cli.capture_output_lines("rclone listremotes", env=self.rclone_env)[0]


context = Context(Options, Config)
