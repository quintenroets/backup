import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from typing import TypeVar

import superpathlib
from cli.commands.commands import CommandItem
from cli.commands.runner import Runner

from backup.context import context

from .filters import FiltersCreator
from .sync_config import SyncConfig

Path = TypeVar("Path", bound=superpathlib.Path)


@dataclass
class CliRunner:
    config: SyncConfig
    push: bool = False
    action: str | None = None
    reverse: bool = False

    @property
    def root(self) -> bool:
        dest = self.config.source if self.reverse else self.config.dest
        return dest.is_root

    def run(self) -> subprocess.CompletedProcess[str]:
        with self.create_runner() as runner:
            return runner.run()

    def capture_output(self, *args: CommandItem) -> str:
        with self.create_runner(*args) as runner:
            return runner.capture_output()

    @contextmanager
    def create_runner(self, *args: CommandItem) -> Iterator[Runner[str]]:
        filters_path = self.create_filters_path()
        command_parts = self.generate_command_parts(filters_path, *args)
        command = tuple(command_parts)
        with filters_path:
            yield Runner(command, root=self.root, kwargs={"env": context.rclone_env})

    def generate_command_parts(
        self,
        filters_path: Path,
        *args: CommandItem,
    ) -> Iterator[CommandItem]:
        if self.root:
            yield "-E"
        yield "rclone"
        yield from self.generate_action_parts()
        yield from args
        yield from ("--filter-from", filters_path, *self.config.options, "--skip-links")
        for name, value in asdict(context.config.rclone).items():
            yield f"--{name.replace('_', '-')}={value}"

    def generate_action_parts(self) -> Iterator[CommandItem]:
        if self.push:
            self.action = "sync"
        if self.action is not None:
            yield self.action
            if self.reverse:
                yield from (self.config.dest, self.config.source)
            else:
                yield from (self.config.source, self.config.dest)
        if self.push:
            yield from ("--create-empty-src-dirs", "--progress")
            if self.root:
                yield "--no-update-dir-modtime"

    def create_filters_path(self) -> superpathlib.Path:
        if not self.config.filter_rules:
            FiltersCreator(self.config).create_filters_from_paths()
        path = superpathlib.Path.tempfile()
        path.lines = self.config.filter_rules
        return path
