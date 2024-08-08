import os
import subprocess
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, field

from cli.commands.commands import CommandItem
from cli.commands.runner import Runner

from backup.context import context
from backup.models import Path
from backup.utils import setup


@dataclass
class Rclone:
    source: Path = field(default_factory=context.extract_backup_source)
    dest: Path = field(default_factory=context.extract_backup_dest)
    filter_rules: list[str] = field(default_factory=list)
    options: list[CommandItem] = field(default_factory=list)
    root: bool = False

    def __post_init__(self) -> None:
        setup.check_setup()

    def capture_output(self, *args: CommandItem) -> str:
        with self.prepared_runner(*args) as runner:
            return runner.capture_output()

    def run(self, *args: CommandItem) -> subprocess.CompletedProcess[str]:
        with self.prepared_runner(*args) as runner:
            return runner.run()

    @contextmanager
    def prepared_runner(self, *args: CommandItem) -> Iterator[Runner[str]]:
        filters_path = self.create_filters_path()
        command_parts = self.generate_cli_command_parts(
            *args,
            filters_path=filters_path,
        )
        command = tuple(command_parts)
        env = os.environ | {"RCLONE_CONFIG_PASS": context.secrets.rclone}
        env.pop("RCLONE_PASSWORD_COMMAND", None)
        kwargs = {"env": env}
        with filters_path:
            yield Runner(command, root=self.root, kwargs=kwargs)

    def generate_cli_command_parts(
        self,
        *args: CommandItem,
        filters_path: Path,
    ) -> Iterator[CommandItem]:
        if self.root:
            yield "-E"
        yield "rclone"
        yield from self.generate_substituted_paths(*args)
        yield from ("--filter-from", filters_path)
        yield from self.options
        yield from self.generate_options()

    @classmethod
    def generate_substituted_paths(cls, *args: CommandItem) -> Iterator[CommandItem]:
        if context.username:
            for arg in args:
                if isinstance(arg, Path) and arg.parts[0] == Path.remote.name:
                    user_home = str(Path.HOME.with_name(context.username))
                    yield str(arg).replace(str(Path.HOME), user_home)
                else:
                    yield arg
        else:
            yield from args  # pragma: nocover

    def create_filters_path(self) -> Path:
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
