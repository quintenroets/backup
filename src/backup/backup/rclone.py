import subprocess
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

import cli
from cli.commands.commands import CommandItem

from ..context import context
from ..models import Path
from ..utils import setup


@dataclass
class Rclone:
    source: Path = Path("/")
    dest: Path = Path.remote
    filter_rules: list[str] = field(default_factory=list)
    options: list[CommandItem] = field(default_factory=list)
    runner: Callable = None
    root: bool = False

    def __post_init__(self) -> None:
        setup.check_setup()

    def capture_output(self, *args: CommandItem) -> str:
        with self.prepared_command(*args) as command:
            return cli.capture_output(command)

    def run(self, *args: CommandItem) -> subprocess.CompletedProcess:
        with self.prepared_command(*args) as command:
            env = {"RCLONE_CONFIG_PASS": context.secrets.rclone}
            return cli.run(command, env=env)

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
