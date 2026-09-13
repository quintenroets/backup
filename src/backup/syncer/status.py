from collections.abc import Iterable, Iterator
from dataclasses import dataclass

import cli
from cli.commands.runner import Runner
from superpathlib import Path

from backup.models import Change, Changes, ChangeTypes
from backup.utils import generate_output_lines
from backup.utils.error_handling import create_malformed_filters_error

from .sync_config import SyncConfig


@dataclass
class StatusProcessor:
    config: SyncConfig
    quiet: bool = False

    def capture_changes(self, runner: Runner[str]) -> tuple[Changes, list[Path]]:
        runner.quiet = self.quiet
        try:
            changes = list(self.generate_changes(runner))
        except cli.CalledProcessError as exception:
            raise create_malformed_filters_error(
                self.config.filter_rules,
            ) from exception
        preserved = ChangeTypes.preserved
        paths_without_change = [
            change.path for change in changes if change.type == preserved
        ]
        changes = [change for change in changes if change.type != preserved]
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
