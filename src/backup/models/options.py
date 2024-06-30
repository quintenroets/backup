from dataclasses import dataclass, field
from typing import Annotated

import typer

from .action import Action
from .path import Path


class Help:
    action: str = "The action to do"
    configure: str = "Open configuration"
    confirm_push: str = "Ask confirmation before pushing"
    sub_check: str = "only check subpath of current working directory"
    include_browser: str = "Include browser config files"
    diff_all: str = "diff all files"
    no_sync: str = "don't sync remote changes when pulling from remote"
    paths: str = "The paths to run the action on"


@dataclass
class Options:
    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.push
    paths: Annotated[list[Path], typer.Argument(help=Help.paths)] = field(
        default_factory=list,
    )
    configure: Annotated[bool, typer.Option(help=Help.configure)] = False
    confirm_push: Annotated[bool, typer.Option(help=Help.configure)] = True
    sub_check: Annotated[bool, typer.Option(help=Help.sub_check)] = False
    include_browser: Annotated[bool, typer.Option(help=Help.include_browser)] = False
    show_file_diffs: bool = False
    diff_all: Annotated[bool, typer.Option(help=Help.diff_all)] = False
    export_resume_changes: bool = False
    no_sync: Annotated[bool, typer.Option(help=Help.no_sync)] = False
    config_path: Path = Path.rclone_command_config
