import select
import subprocess
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import IO

import cli
from cli.commands.runner import Runner
from superpathlib import Path

from backup.models import Change, Changes, ChangeType

from .filters import create_malformed_filters_error
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
        paths_without_change = [
            change.path for change in changes if change.type == ChangeType.preserved
        ]
        changes = [change for change in changes if change.type != ChangeType.preserved]
        return changes, paths_without_change

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
            type_ = ChangeType(line[0])
            yield Change(Path(line[2:]), type_, self.config.source, self.config.dest)


def generate_output_lines(runner: Runner[str]) -> Iterator[str]:
    runner.stdout = subprocess.PIPE
    runner.stderr = subprocess.PIPE
    process = runner.launch()
    extracted_outputs = extract_output_lines(process)
    error_lines = []
    output_generated = False
    for line, is_stdout in extracted_outputs:
        if is_stdout:
            output_generated = True
            yield line
        else:
            error_lines.append(line)
    if not output_generated and error_lines:
        message = "\n".join(error_lines)
        raise cli.CalledProcessError(message)


def extract_output_lines(process: subprocess.Popen[str]) -> Iterator[tuple[str, bool]]:
    streams = process.stdout, process.stderr
    outputs: list[IO[str]] = [f for f in streams if f is not None]
    while outputs:
        readable_outputs, _, _ = select.select(outputs, [], [])
        for output in readable_outputs:
            line = output.readline().strip()
            if line:
                yield line, output is process.stdout
            else:
                outputs.remove(output)
