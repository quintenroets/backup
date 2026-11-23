from __future__ import annotations

import os
import re
from dataclasses import asdict, dataclass, field, replace
from functools import cache
from typing import TYPE_CHECKING, Self, Unpack

import cli
from package_utils.secrets_ import load_secret
from superpathlib import Path

from .context import context
from .models import Change, ChangeType, PathRule

if TYPE_CHECKING:
    import subprocess
    from collections.abc import Iterable, Iterator

    from cli.commands import RunOptions

    Process = subprocess.CompletedProcess[str]


@dataclass
class Syncer:
    source: Path
    dest: Path
    rules: list[PathRule] = field(default_factory=list)

    def sync(self, **kwargs: Unpack[RunOptions]) -> Process:
        return self.run("sync", "--create-empty-src-dirs", "--progress", **kwargs)

    def list_mtimes(self) -> Iterator[dict[str, str]]:
        args = "lsf", "-R", "--files-only", "--format=pt", "--time-format=unix"
        for directory in (self.source, self.dest):
            output = self.run_rclone(*args, directory, capture_output=True).stdout
            yield dict(line.rsplit(";", 1) for line in output.splitlines())

    def capture_status(self, *, reverse: bool = False) -> list[Change]:
        syncer = self.reversed if reverse else self
        process = syncer.run("check", "--combined=-", check=False, capture_output=True)
        if not process.stdout:
            process.check_returncode()
        lines = process.stdout.splitlines()
        changes = [Change(Path(line[2:]), ChangeType(line[0])) for line in lines]
        preserved = ChangeType.preserved
        if unchanged := [change.path for change in changes if change.type == preserved]:
            # Update modified times to avoid checking again in the future
            self.with_paths(unchanged).sync()
        return [change for change in changes if change.type != preserved]

    def export_files(self, format_: str) -> Process:
        args = "copy", "--drive-export-formats", format_
        return self.reversed.run(*args, capture_output=True)

    def run(self, verb: str, *args: object, **kwargs: Unpack[RunOptions]) -> Process:
        return self.run_rclone(verb, self.source, self.dest, *args, **kwargs)

    def run_rclone(self, *args: object, **kwargs: Unpack[RunOptions]) -> Process:
        filters = (line for rule in self.rules for line in create_filters(rule))
        options = kwargs | {"input": "\n".join(filters), "env": load_rclone_env()}
        return cli.run(*self.generate_command(*args), **options)

    def generate_command(self, *args: object) -> Iterator[object]:
        existing = (path for path in (self.dest, *self.dest.parents) if path.exists())
        root = ":" not in self.dest.parts[0] and not os.access(next(existing), os.W_OK)
        yield "sudo -E rclone --no-update-dir-modtime" if root else "rclone"
        yield from (*args, "--filter-from=-", "--skip-links")
        for name, value in asdict(context.config.rclone).items():
            yield f"--{name.replace('_', '-')}={value}"

    @property
    def reversed(self) -> Self:
        return replace(self, source=self.dest, dest=self.source)

    def with_paths(self, paths: Iterable[Path]) -> Self:
        includes = [PathRule(path, include=True) for path in paths]
        return replace(self, rules=[*includes, PathRule(Path(), include=False)])


def create_syncer(path: Path) -> Syncer:
    source = Path("/")
    dest = Path(resolve_remote())
    if path.is_relative_to(Path.HOME):
        source = Path.HOME
        dest /= "home"
    return Syncer(source, dest).with_paths([path.relative_to(source)])


@cache
def resolve_remote() -> str:
    return cli.capture_output_lines("rclone listremotes", env=load_rclone_env())[0]


def create_filters(rule: PathRule) -> tuple[str, str]:
    sign = "+" if rule.include else "-"
    path = re.escape(str(rule.path)) if rule.path.parts else "**"
    return f"{sign} /{path}", f"{sign} /{path}/**"


@cache
def load_rclone_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
        env["RCLONE_CONFIG_PASS"] = load_secret("rclone")
    return env
