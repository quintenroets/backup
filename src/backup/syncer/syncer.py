import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TypeVar

import superpathlib
from cli.commands.commands import CommandItem

from backup.models import Changes
from backup.models import Path as BackupPath
from backup.utils import setup

from .cli_runner import CliRunner
from .status import StatusProcessor
from .sync_config import SyncConfig

Path = TypeVar("Path", bound=superpathlib.Path)


@dataclass
class Syncer:
    config: SyncConfig = field(default_factory=lambda: SyncConfig())

    def __post_init__(self) -> None:
        setup.check_setup()

    def cli_runner(
        self,
        *,
        push: bool = False,
        action: str | None = None,
        reverse: bool = False,
    ) -> CliRunner:
        return CliRunner(self.config, push=push, action=action, reverse=reverse)

    def run(self, *args: CommandItem) -> subprocess.CompletedProcess[str]:
        return self.cli_runner().run(*args)

    def capture_output(self, *args: CommandItem) -> str:
        return self.cli_runner().capture_output(*args)

    def push(self, *, reverse: bool = False) -> subprocess.CompletedProcess[str]:
        return self.cli_runner(push=True, reverse=reverse).run()

    def capture_push(self, *, reverse: bool = False) -> str:
        return self.cli_runner(push=True, reverse=reverse).capture_output()

    def pull(self) -> subprocess.CompletedProcess[str]:
        return self.push(reverse=True)

    def capture_pull(self) -> str:
        return self.capture_push(reverse=True)

    def export_pdfs(self) -> str:
        return self.export_files("pdp")

    def export_files(self, export_format: str) -> str:
        return self.cli_runner(action="copy", reverse=True).capture_output(
            "--drive-export-formats",
            export_format,
        )

    def capture_status(
        self,
        *,
        quiet: bool = False,
        reverse: bool = False,
        is_cache: bool = False,
    ) -> Changes:
        runner_factory = self.cli_runner(action="check", reverse=reverse)
        with runner_factory.create_runner("--combined", "-") as runner:
            changes, no_change_paths = StatusProcessor(
                self.config,
                quiet,
                is_cache=is_cache,
            ).capture_changes(runner)
            if no_change_paths:
                # Update modified times to avoid checking again in the future
                Syncer(self.config.with_paths(no_change_paths)).push()
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
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").astimezone(
                    tz=timezone.utc,
                )
                path = BackupPath(path_str)
                yield path, date
