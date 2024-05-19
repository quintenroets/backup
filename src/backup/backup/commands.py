import subprocess
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any

import cli
from cli.commands.commands import CommandItem

from ..models import Change, Changes, ChangeType, Path
from ..utils import generate_output_lines
from . import paths


@dataclass
class Backup(paths.Rclone):
    def capture_status(self, quiet: bool = False) -> Changes:
        options = "check", "--combined", "-"
        with self.prepared_command_with_locations(*options, reverse=False) as command:
            print("prepared")
            return self.get_changes(*command, quiet=quiet)

    def pull(self) -> subprocess.CompletedProcess[str]:
        return self.push(reverse=True)

    def capture_pull(self) -> str:
        return self.capture_push(reverse=True)

    @contextmanager
    def prepared_push_command(
        self, reverse: bool = False
    ) -> Iterator[Iterator[CommandItem]]:
        options = "sync", "--create-empty-src-dirs", "--progress"
        with self.prepared_command_with_locations(*options, reverse=reverse) as command:
            yield command

    def push(self, reverse: bool = False) -> subprocess.CompletedProcess[str]:
        with self.prepared_push_command(reverse=reverse) as command:
            return cli.run(*command)

    def capture_push(self, reverse: bool = False) -> str:
        with self.prepared_push_command(reverse=reverse) as command:
            return cli.capture_output(*command)

    @contextmanager
    def prepared_command_with_locations(
        self, action: str, *args: CommandItem, reverse: bool = False, **kwargs: Any
    ) -> Iterator[Iterator[CommandItem]]:
        if reverse:
            source, dest = self.dest, self.source
        else:
            source, dest = self.source, self.dest
        args = action, source, dest, *args
        with super().prepared_command(*args, **kwargs) as command:
            yield command

    def get_changes(self, *args: Any, **kwargs: Any) -> Changes:
        change_results = self.generate_change_results(*args, **kwargs)
        changes = self.extract_changes(change_results)
        return Changes(list(changes))

    def extract_changes(self, change_results: Iterable[Change]) -> Iterator[Change]:
        no_change_results = []
        for result in change_results:
            if result.type == ChangeType.preserved:
                no_change_results.append(result)
            else:
                yield result

        if no_change_results:
            self.update_paths_without_change(no_change_results)

    def update_paths_without_change(self, results: list[Change]) -> None:
        """
        Update modified times to avoid checking again in the future.
        """
        no_change_paths = [result.path for result in results]
        if self.dest.is_relative_to(Path.backup_cache):  # noqa
            for path in no_change_paths:
                dest = self.dest / path
                if dest.tag is None:
                    dest.tag = str(dest.mtime)  # save original mtime for remote syncing

        backup = Backup(source=self.source, dest=self.dest, paths=no_change_paths)
        backup.push()

    def generate_change_results(
        self, *args: CommandItem, quiet: bool = False, **kwargs: Any
    ) -> Iterator[Change]:
        status_lines: Iterable[str] = generate_output_lines(*args, **kwargs)
        if not quiet:
            status_lines = cli.track_progress(
                status_lines,
                description="Checking",
                unit="files",
                total=len(self.paths) if self.paths else None,
                cleanup_after_finish=True,
            )
        for line in status_lines:
            yield Change.from_pattern(line, self.source, self.dest)
