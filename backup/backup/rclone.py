from collections.abc import Callable
from dataclasses import dataclass, field

import cli

from ..utils import Path, setup


@dataclass
class Rclone:
    source: Path | str = Path("/")
    dest: Path | str = Path.remote
    filter_rules: list[str] = field(default_factory=list)
    options: list[str | set | dict] = field(default_factory=list)
    overwrite_newer: bool = True
    quiet: bool = False
    retries: int = 5
    retries_sleep: str = "30s"
    order_by: str = "size,desc"  # handle largest files first
    drive_import_formats = "docx, xlsx"
    runner: Callable = None
    root: bool = False

    def __post_init__(self):
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
        }
        yield options_dict

    def run(self, *args: str | dict):
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

    def use_runner(self, runner):
        self.runner = runner

    def reset_runner(self):
        self.runner = cli.get if self.quiet else cli.run
