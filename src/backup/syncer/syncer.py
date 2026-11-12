import subprocess
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from cli.commands.commands import CommandItem

from backup.models import Change, Changes, ChangeType
from backup.path import Path as BackupPath

from .cli_runner import CliRunner
from .sync_config import SyncConfig


@dataclass
class Syncer:
    config: SyncConfig

    def capture_output(self, *args: CommandItem) -> str:
        return CliRunner(self.config).create_runner(*args).capture_output()

    def push(self) -> subprocess.CompletedProcess[str]:
        return CliRunner(self.config, "sync").create_runner().run()

    def capture_push(self) -> str:
        return CliRunner(self.config, "sync").create_runner().capture_output()

    def capture_pull(self) -> str:
        return Syncer(self.config.reversed).capture_push()

    def export_files(self, export_format: str) -> str:
        args = "--drive-export-formats", export_format
        runner = CliRunner(self.config.reversed, "copy").create_runner(*args)
        return runner.capture_output()

    def capture_status(self, *, reverse: bool = False) -> Changes:
        config = self.config.reversed if reverse else self.config
        runner = CliRunner(config, "check").create_runner("--combined", "-")
        runner.check = False
        process = runner.run(capture_output=True)
        if not process.stdout:
            process.check_returncode()
        lines = process.stdout.splitlines()
        changes = [Change(BackupPath(line[2:]), ChangeType(line[0])) for line in lines]
        preserved = ChangeType.preserved
        if unchanged := [change.path for change in changes if change.type == preserved]:
            # Update modified times to avoid checking again in the future
            Syncer(self.config.with_paths(unchanged)).push()
        return [change for change in changes if change.type != preserved]

    def generate_paths_with_time(self) -> Iterator[tuple[BackupPath, datetime]]:
        lines = self.capture_output("lsl", self.config.dest)
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
