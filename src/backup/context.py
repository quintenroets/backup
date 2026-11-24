from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING, Annotated

from package_utils.context import Context

if TYPE_CHECKING:
    import typer


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


context: Context[Options, None, None] = Context(Options)
