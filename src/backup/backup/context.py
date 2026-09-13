from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

from package_utils.context import Context

from .models import Action, Config, Path

if TYPE_CHECKING:
    import typer  # pragma: nocover


class Help:
    action: str = "The action to do"
    confirm: str = "Ask confirmation before applying changes"
    diff: str = "Show content diffs of changed files before confirming"
    sub_check: str = "only check subpath of current working directory"
    remote: str = "rclone remote to back up to"
    config_path: str = "Configuration describing what to back up"


@dataclass
class Options:
    """How one run behaves, as opposed to what a config says to back up."""

    action: Annotated[Action, typer.Argument(help=Help.action)] = Action.push
    confirm: Annotated[bool, typer.Option(help=Help.confirm)] = True
    diff: Annotated[bool, typer.Option(help=Help.diff)] = False
    sub_check: Annotated[bool, typer.Option(help=Help.sub_check)] = False
    remote: Annotated[str | None, typer.Option(help=Help.remote)] = None
    config_path: Annotated[Path, typer.Option(help=Help.config_path)] = Path.config


context: Context[Options, Config, None] = Context(
    Options,
    Config,
)
