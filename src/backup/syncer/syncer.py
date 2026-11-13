import subprocess
from dataclasses import dataclass

import superpathlib
from cli.commands.commands import CommandItem

from backup.models import Change, Changes, ChangeType
from backup.path import Path as BackupPath

from .cli_runner import CliRunner, resolve_remote
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


def create_syncer(path: superpathlib.Path) -> Syncer:
    source = BackupPath.backup_source
    dest = BackupPath(resolve_remote())
    if path.is_relative_to(BackupPath.HOME):
        source = BackupPath.HOME
        dest /= "home"
    return Syncer(SyncConfig(source, dest).with_paths([path.relative_to(source)]))
