from collections.abc import Callable
from dataclasses import dataclass, field

import cli

from ..models import Path
from ..utils import setup

# TODO: use separate config dataclass and use .dict() in generate_options


@dataclass
class Rclone:
    source: Path = field(default_factory=lambda: Path("/"))
    dest: Path = Path.remote
    filter_rules: list[str] = field(default_factory=list)
    options: list[str | set | dict] = field(default_factory=list)
    overwrite_newer: bool = True
    quiet: bool = False
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
        named_options = self.generate_options()
        self.options.extend(named_options)
        self.reset_runner()

    def generate_options(self):
        yield "--skip-links"
        if not self.overwrite_newer:
            yield "--update"

        options_dict = {
            "retries": self.retries,
            "retries-sleep": self.retries_sleep,
            "order-by": self.order_by,
            "drive-import-formats": self.drive_import_formats,
            "checkers": self.n_checkers,
            "transfers": self.n_parallel_transfers,
        }
        yield options_dict

    def run(self, *args: str | dict | Path) -> None:
        filters_path = self.create_filters_path()
        with filters_path:
            args = "rclone", *args, "--filter-from", filters_path, *self.options
            result = self.runner(*args, root=self.root)

        self.reset_runner()
        return result

    def create_filters_path(self):
        path = Path.tempfile()
        path.lines = self.filter_rules
        return path

    def use_runner(self, runner) -> None:
        self.runner = runner

    def reset_runner(self) -> None:
        self.runner = cli.capture_output if self.quiet else cli.run
