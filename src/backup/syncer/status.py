from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

import cli
from cli.commands.runner import Runner

from backup.models import Change, Changes, ChangeTypes, Path
from backup.utils import generate_output_lines
from backup.utils.error_handling import create_malformed_filters_error

from .sync_config import SyncConfig


@dataclass
class StatusProcessor:
    config: SyncConfig = field(default_factory=lambda: SyncConfig())
    quiet: bool = False
    is_cache: bool = False

    def capture_changes(self, runner: Runner[str]) -> tuple[Changes, list[Path]]:
        runner.quiet = self.quiet
        try:
            changes = list(self.generate_changes(runner))
        except cli.CalledProcessError as exception:
            raise create_malformed_filters_error(
                self.config.filter_rules,
            ) from exception
        paths_without_change = list(self.extract_paths_without_change(changes))
        changes = [change for change in changes if change.type != ChangeTypes.preserved]
        return Changes(changes), paths_without_change

    def generate_changes(self, runner: Runner[str]) -> Iterator[Change]:
        status_lines: Iterable[str] = generate_output_lines(runner)
        if not runner.quiet:
            status_lines = cli.track_progress(
                status_lines,
                description="Checking",
                unit="files",
                total=len(self.config.paths) if self.config.paths else None,
                cleanup_after_finish=True,
            )
        for line in status_lines:
            yield Change.from_pattern(line, self.config.source, self.config.dest)

    def extract_paths_without_change(self, changes: list[Change]) -> Iterator[Path]:
        for change in changes:
            if change.type == ChangeTypes.preserved:
                yield change.path
                if self.is_cache:
                    dest = self.config.dest / change.path
                    if dest.tag is None:
                        # save original mtime for remote syncing
                        dest.tag = str(dest.mtime)
