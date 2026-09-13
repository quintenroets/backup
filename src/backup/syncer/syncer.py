from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from .models import FileState
from .rclone_config import RcloneConfig

if TYPE_CHECKING:
    import subprocess  # pragma: nocover

    from cli.commands.commands import CommandItem  # pragma: nocover

    from .cli_runner import CliRunner  # pragma: nocover
    from .sync_config import SyncConfig  # pragma: nocover


@dataclass
class Syncer:
    config: SyncConfig
    options: RcloneConfig = field(default_factory=RcloneConfig)

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

    def copy_from_remote(self) -> subprocess.CompletedProcess[str]:
        return self.cli_runner(action="copy", reverse=True).run()

    def capture_pull(self) -> str:
        return self.capture_push(reverse=True)

    def export_files(self, export_format: str) -> str:
        return self.cli_runner(action="copy", reverse=True).capture_output(
            "--drive-export-formats",
            export_format,
        )

    def list_remote_files(self) -> dict[str, FileState]:
        output = self.capture_output(
            "lsjson",
            "--recursive",
            "--files-only",
            self.config.dest,
        )
        return parse_remote_files(output)

    def cli_runner(
        self,
        *,
        push: bool = False,
        action: str | None = None,
        reverse: bool = False,
    ) -> CliRunner:
        from .cli_runner import CliRunner  # noqa: PLC0415

        return CliRunner(
            self.config,
            self.options,
            push=push,
            action=action,
            reverse=reverse,
        )


def parse_remote_files(output: str) -> dict[str, FileState]:
    return {
        info["Path"]: FileState(parse_modified_time(info["ModTime"]), info["Size"])
        for info in json.loads(output)
    }


def parse_modified_time(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()
