import itertools
import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from functools import cache

import superpathlib
from cli.commands.commands import CommandItem
from cli.commands.runner import Runner
from package_utils.context.loaders.secrets_ import SecretLoader

from .filters import generate_filters
from .sync_config import SyncConfig


@dataclass
class RcloneConfig:
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers: int = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"
    drive_import_formats: str = "docx, xlsx"


@cache
def load_rclone_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
        env["RCLONE_CONFIG_PASS"] = SecretLoader("rclone").load()
    return env


@dataclass
class CliRunner:
    config: SyncConfig
    options: RcloneConfig = field(default_factory=RcloneConfig)
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
        with filters_path:
            env = {"env": load_rclone_env()}
            yield Runner(command, root=self.root, kwargs=env)

    def create_filters_path(self) -> superpathlib.Path:
        path = superpathlib.Path.tempfile()
        path.lines = list(generate_filters(self.config))
        return path

    def generate_command_parts(
        self,
        filters_path: superpathlib.Path,
        *args: CommandItem,
    ) -> Iterator[CommandItem]:
        if self.root:
            yield "-E"
        yield "rclone"
        parts = (
            self.generate_action_parts(),
            args,
            ("--filter-from", filters_path),
            self.generate_options(),
        )
        yield from itertools.chain(*parts)

    def generate_action_parts(self) -> Iterator[CommandItem]:
        action = "sync" if self.push else self.action
        if action is not None:
            yield action
            if self.reverse:
                yield from (self.config.dest, self.config.source)
            else:
                yield from (self.config.source, self.config.dest)
        if self.push:
            yield from ("--create-empty-src-dirs", "--progress")
            if self.root:
                yield "--no-update-dir-modtime"

    def generate_options(self) -> Iterator[CommandItem]:
        options = self.options
        yield "--skip-links"
        if not options.overwrite_newer:
            yield "--update"

        yield {
            "retries": options.retries,
            "retries-sleep": options.retries_sleep,
            "order-by": options.order_by,
            "drive-import-formats": options.drive_import_formats,
            "checkers": options.n_checkers,
            "transfers": options.n_parallel_transfers,
        }
