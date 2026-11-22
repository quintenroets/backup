import subprocess
from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Self

from cli.commands.commands import CommandItem
from superpathlib import Path

from backup.models import Change, Changes, ChangeType, PathRule

from .cli_runner import CliRunner, resolve_remote


@dataclass
class Syncer:
    source: Path
    dest: Path
    rules: list[PathRule] = field(default_factory=list)

    @property
    def reversed(self) -> Self:
        return replace(self, source=self.dest, dest=self.source)

    def with_paths(self, paths: Iterable[Path]) -> Self:
        includes = [PathRule(path, include=True) for path in paths]
        return replace(self, rules=[*includes, PathRule(Path(), include=False)])

    def capture_output(self, *args: CommandItem) -> str:
        return CliRunner(self).create_runner(*args).capture_output()

    def push(self) -> subprocess.CompletedProcess[str]:
        return CliRunner(self, "sync").create_runner().run()

    def capture_push(self) -> str:
        return CliRunner(self, "sync").create_runner().capture_output()

    def capture_pull(self) -> str:
        return self.reversed.capture_push()

    def export_files(self, export_format: str) -> str:
        args = "--drive-export-formats", export_format
        return CliRunner(self.reversed, "copy").create_runner(*args).capture_output()

    def capture_status(self, *, reverse: bool = False) -> Changes:
        syncer = self.reversed if reverse else self
        runner = CliRunner(syncer, "check").create_runner("--combined", "-")
        runner.check = False
        process = runner.run(capture_output=True)
        if not process.stdout:
            process.check_returncode()
        lines = process.stdout.splitlines()
        changes = [Change(Path(line[2:]), ChangeType(line[0])) for line in lines]
        preserved = ChangeType.preserved
        if unchanged := [change.path for change in changes if change.type == preserved]:
            # Update modified times to avoid checking again in the future
            self.with_paths(unchanged).push()
        return [change for change in changes if change.type != preserved]


def create_syncer(path: Path) -> Syncer:
    source = Path("/")
    dest = Path(resolve_remote())
    if path.is_relative_to(Path.HOME):
        source = Path.HOME
        dest /= "home"
    return Syncer(source, dest).with_paths([path.relative_to(source)])
