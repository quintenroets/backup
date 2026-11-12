import os
import re
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from functools import cache

import cli
from cli.commands.commands import CommandItem
from cli.commands.runner import Runner
from package_utils.secrets_ import load_secret

from backup.context import context
from backup.models import PathRule

from .sync_config import SyncConfig


@dataclass
class CliRunner:
    config: SyncConfig
    action: str | None = None
    reverse: bool = False

    @property
    def root(self) -> bool:
        path = self.config.source if self.reverse else self.config.dest
        existing = (path_ for path_ in (path, *path.parents) if path_.exists())
        return ":" not in path.parts[0] and not os.access(next(existing), os.W_OK)

    def create_runner(self, *args: CommandItem) -> Runner[str]:
        command = tuple(self.generate_command_parts(*args))
        filters = (line for rule in self.config.rules for line in create_filters(rule))
        kwargs = {"env": load_rclone_env()}
        return Runner(command, root=self.root, input="\n".join(filters), kwargs=kwargs)

    def generate_command_parts(self, *args: CommandItem) -> Iterator[CommandItem]:
        if self.root:
            yield "-E"
        yield from ("rclone", *self.generate_action_parts(), *args)
        yield from ("--filter-from", "-", "--skip-links")
        for name, value in asdict(context.config.rclone).items():
            yield f"--{name.replace('_', '-')}={value}"

    def generate_action_parts(self) -> Iterator[CommandItem]:
        if self.action is not None:
            yield self.action
            if self.reverse:
                yield from (self.config.dest, self.config.source)
            else:
                yield from (self.config.source, self.config.dest)
        if self.action == "sync":
            yield from ("--create-empty-src-dirs", "--progress")
            if self.root:
                yield "--no-update-dir-modtime"


def create_filters(rule: PathRule) -> tuple[str, str]:
    sign = "+" if rule.include else "-"
    path = re.escape(str(rule.path)) if rule.path.parts else "**"
    return f"{sign} /{path}", f"{sign} /{path}/**"


@cache
def resolve_remote() -> str:
    return cli.capture_output_lines("rclone listremotes", env=load_rclone_env())[0]


@cache
def load_rclone_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
        env["RCLONE_CONFIG_PASS"] = load_secret("rclone")
    return env
