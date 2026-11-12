import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import TypeVar

import superpathlib
from cli.commands.commands import CommandItem
from cli.commands.runner import Runner

from backup.models import Changes
from backup.path import Path as BackupPath

from .cli_runner import CliRunner
from .status import StatusProcessor
from .sync_config import SyncConfig

Path = TypeVar("Path", bound=superpathlib.Path)


@dataclass
class Syncer:
    config: SyncConfig

    def create_runner(
        self,
        *args: CommandItem,
        action: str | None = None,
        reverse: bool = False,
    ) -> Runner[str]:
        return CliRunner(self.config, action, reverse=reverse).create_runner(*args)

    def capture_output(self, *args: CommandItem) -> str:
        return self.create_runner(*args).capture_output()

    def push(self, *, reverse: bool = False) -> subprocess.CompletedProcess[str]:
        return self.create_runner(action="sync", reverse=reverse).run()

    def capture_push(self, *, reverse: bool = False) -> str:
        return self.create_runner(action="sync", reverse=reverse).capture_output()

    def pull(self) -> subprocess.CompletedProcess[str]:
        return self.push(reverse=True)

    def capture_pull(self) -> str:
        return self.capture_push(reverse=True)

    def export_files(self, export_format: str) -> str:
        args = "--drive-export-formats", export_format
        return self.create_runner(*args, action="copy", reverse=True).capture_output()

    def capture_status(
        self,
        *,
        quiet: bool = False,
        reverse: bool = False,
    ) -> Changes:
        runner = self.create_runner("--combined", "-", action="check", reverse=reverse)
        processor = StatusProcessor(self.config, quiet)
        changes, no_change_paths = processor.capture_changes(runner)
        if no_change_paths:
            # Update modified times to avoid checking again in the future
            Syncer(replace(self.config, paths=no_change_paths)).push()
        return changes

    def generate_paths_with_time(
        self,
        path: Path | None = None,
    ) -> Iterator[tuple[BackupPath, datetime]]:
        lines = self.capture_output("lsl", path or self.config.dest)
        return extract_paths_with_time(lines)


def extract_paths_with_time(lines: str) -> Iterator[tuple[BackupPath, datetime]]:
    for line in lines.splitlines():
        if line:
            parts = line.split()
            date_str = " ".join(parts[1:3]).split(".")[0]
            path_str = " ".join(parts[3:])
            if path_str:
                format_ = "%Y-%m-%d %H:%M:%S"
                date = datetime.strptime(date_str, format_).astimezone(UTC)
                path = BackupPath(path_str)
                yield path, date
