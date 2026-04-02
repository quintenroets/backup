from dataclasses import dataclass, field
from typing import Annotated

import typer

from backup.models import Path

from .action import Action


class Help:
    action: str = "The action to do"
    configure: str = "Open configuration"
    confirm_push: str = "Ask confirmation before pushing"
    sub_check: str = "only check subpath of current working directory"
    include_browser: str = "Include browser config files"
    diff_all: str = "diff all files"
    cache_only: str = "pull from local cache without syncing from remote"
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
    cache_only: Annotated[bool, typer.Option(help=Help.cache_only)] = False
