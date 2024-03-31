import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import TypeVar

import cli
from cli.commands.commands import CommandItem

from ..models import Path
from ..utils import setup

# TODO: use separate config dataclass and use .dict() in generate_options
T = TypeVar("T")


@dataclass
class Rclone:
    source: Path = Path("/")
    dest: Path = Path.remote
    filter_rules: list[str] = field(default_factory=list)
    options: list[str | set | dict] = field(default_factory=list)
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"  # handle largest files first
    drive_import_formats = "docx, xlsx"
    runner: Callable = None
    root: bool = False

    def __post_init__(self) -> None:
        setup.check_setup()

    def capture_output(self, *args: CommandItem) -> str:
        with self.prepared_command(*args) as command:
            return cli.capture_output(command)

    def run(self, *args: CommandItem) -> subprocess.CompletedProcess:
        with self.prepared_command(*args) as command:
            return cli.run(command)

    @contextmanager
    def prepared_command(self, *args: CommandItem) -> Iterator[list[CommandItem]]:
        filters_path = self.create_filters_path()
        command = self.generate_cli_command_parts(*args, filters_path=filters_path)
        with filters_path:
            yield list(command)

    def generate_cli_command_parts(
        self, *args: CommandItem, filters_path: Path
    ) -> Iterator[CommandItem]:
        yield from ("rclone", *args, "--filter-from", filters_path)
        yield from self.options
        yield from self.generate_options()

    def create_filters_path(self):
        path = Path.tempfile()
        path.lines = self.filter_rules
        return path

    def generate_options(self):
        yield "--skip-links"
        if not self.overwrite_newer:
            yield "--update"

        yield {
            "retries": self.retries,
            "retries-sleep": self.retries_sleep,
            "order-by": self.order_by,
            "drive-import-formats": self.drive_import_formats,
            "checkers": self.n_checkers,
            "transfers": self.n_parallel_transfers,
        }
