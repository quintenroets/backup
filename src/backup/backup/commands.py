import subprocess
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass

import cli
from cli.commands.commands import CommandItem
from cli.commands.runner import Runner

from backup.models import Change, Changes, ChangeType, Path
from backup.utils import generate_output_lines
from backup.utils.error_handling import create_malformed_filters_error

from . import paths


@dataclass
class Backup(paths.Rclone):
    def capture_status(self, *, quiet: bool = False, reverse: bool = False) -> Changes:
        options = "check", "--combined", "-"
        with self.prepared_runner_with_locations(*options, reverse=reverse) as runner:
            runner.quiet = quiet
            try:
                return self.capture_changes(runner)
            except cli.CalledProcessError:
                raise create_malformed_filters_error(self.filter_rules) from None

    def pull(self) -> subprocess.CompletedProcess[str]:
        return self.push(reverse=True)

    def capture_pull(self) -> str:
        return self.capture_push(reverse=True)

    @contextmanager
    def prepared_push_runner(self, *, reverse: bool = False) -> Iterator[Runner[str]]:
        options = "sync", "--create-empty-src-dirs", "--progress"
        with self.prepared_runner_with_locations(*options, reverse=reverse) as runner:
            yield runner

    def push(self, *, reverse: bool = False) -> subprocess.CompletedProcess[str]:
        with self.prepared_push_runner(reverse=reverse) as runner:
            return runner.run()

    def capture_push(self, *, reverse: bool = False) -> str:
        with self.prepared_push_runner(reverse=reverse) as runner:
            return runner.capture_output()

    @contextmanager
    def prepared_runner_with_locations(
        self,
        action: str,
        *args: CommandItem,
        reverse: bool = False,
    ) -> Iterator[Runner[str]]:
        if reverse:
            source, dest = self.dest, self.source
        else:
            source, dest = self.source, self.dest
        args = action, source, dest, *args
        with super().prepared_runner(*args) as runner:
            yield runner

    def capture_changes(self, runner: Runner[str]) -> Changes:
        change_results = self.generate_change_results(runner)
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
        if self.dest.is_relative_to(Path.backup_cache):  # pragma: no cover
            for path in no_change_paths:
                dest = self.dest / path
                if dest.tag is None:
                    dest.tag = str(dest.mtime)  # save original mtime for remote syncing

        backup = Backup(source=self.source, dest=self.dest, paths=no_change_paths)
        backup.push()

    def generate_change_results(self, runner: Runner[str]) -> Iterator[Change]:
        status_lines: Iterable[str] = generate_output_lines(runner)
        if not runner.quiet:
            status_lines = cli.track_progress(
                status_lines,
                description="Checking",
                unit="files",
                total=len(self.paths) if self.paths else None,
                cleanup_after_finish=True,
            )
        for line in status_lines:
            yield Change.from_pattern(line, self.source, self.dest)
