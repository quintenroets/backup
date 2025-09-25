import itertools
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
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

    def run(self, *args: CommandItem) -> subprocess.CompletedProcess[str]:
        with self.create_runner(*args) as runner:
            return runner.run()

    def capture_output(self, *args: CommandItem) -> str:
        with self.create_runner(*args) as runner:
            return runner.capture_output()

    @contextmanager
    def create_runner(self, *args: CommandItem) -> Iterator[Runner[str]]:
        filters_path = self.create_filters_path()
        command_parts = self.generate_command_parts(filters_path, *args)
        command = tuple(command_parts)
        env = os.environ | {"RCLONE_CONFIG_PASS": context.secrets.rclone}
        env.pop("RCLONE_PASSWORD_COMMAND", None)
        kwargs = {"env": env}
        with filters_path:
            yield Runner(command, root=self.root, kwargs=kwargs)

    def generate_command_parts(
        self,
        filters_path: Path,
        *args: CommandItem,
    ) -> Iterator[CommandItem]:
        if self.root:
            yield "-E"
        yield "rclone"
        parts = (
            self.generate_action_parts(),
            args,
            ("--filter-from", filters_path),
            self.config.options,
            self.generate_options(),
        )
        yield from itertools.chain(*parts)

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

    @classmethod
    def generate_options(cls) -> Iterator[CommandItem]:
        config = context.config
        yield "--skip-links"
        if not config.overwrite_newer:
            yield "--update"

        yield {
            "retries": config.retries,
            "retries-sleep": config.retries_sleep,
            "order-by": config.order_by,
            "drive-import-formats": config.drive_import_formats,
            "checkers": config.n_checkers,
            "transfers": config.n_parallel_transfers,
        }
