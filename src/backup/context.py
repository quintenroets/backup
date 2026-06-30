import os
from dataclasses import dataclass
from enum import Enum
from functools import cached_property
from typing import Annotated, cast

import cli
import typer
from package_utils.context import Context as Context_
from package_utils.context.loaders.secrets_ import SecretLoader

from backup.models import Path
from backup.storage.storage import Storage


class Action(str, Enum):
    push = "push"
    pull = "pull"


@dataclass
class Config:
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"  # handle largest files first
    drive_import_formats = "docx, xlsx"
    max_backup_size: int = int(50e6)


class Help:
    action: str = "The action to do"
    configure: str = "Open configuration"
    confirm_push: str = "Ask confirmation before pushing"
    sub_check: str = "only check subpath of current working directory"
    cache_only: str = "pull from local cache without syncing from remote"
    remote: str = "rclone remote to back up to"


@dataclass
class Options:
    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.push
    configure: Annotated[bool, typer.Option(help=Help.configure)] = False
    confirm_push: Annotated[bool, typer.Option(help=Help.configure)] = True
    sub_check: Annotated[bool, typer.Option(help=Help.sub_check)] = False
    export_resume_changes: bool = False
    cache_only: Annotated[bool, typer.Option(help=Help.cache_only)] = False
    remote: Annotated[str | None, typer.Option(help=Help.remote)] = None


class Context(Context_[Options, Config, None]):
    @cached_property
    def storage(self) -> Storage:
        return Storage()

    @cached_property
    def sub_check_path(self) -> Path | None:  # pragma: no cover
        if self.options.export_resume_changes:
            sub_check_path = Path.resume
        elif self.options.sub_check:
            sub_check_path = Path.cwd()
        else:
            sub_check_path = None
        return cast("Path | None", sub_check_path)

    @cached_property
    def rclone_env(self) -> dict[str, str]:
        env = dict(os.environ)
        if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
            env["RCLONE_CONFIG_PASS"] = SecretLoader("rclone").load()
        return env

    @cached_property
    def remote(self) -> str:
        return (
            self.options.remote
            if self.options.remote is not None
            else cli.capture_output_lines("rclone listremotes", env=self.rclone_env)[0]
        )


context = Context(Options, Config)
