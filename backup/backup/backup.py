from collections.abc import Iterable
from dataclasses import dataclass

import cli

from ..utils import Change, Changes, ChangeType, generate_output_lines
from . import paths


@dataclass
class Backup(paths.Rclone):
    reverse: bool = False

    def compare(self):
        return self.status()

    def move(self):
        return self.start("sync", "--create-empty-src-dirs", "--progress")

    def push(self):
        return self.move()

    def copy(self):
        return self.start("copy", "--progress")

    def pull(self):
        self.reverse = True
        self.move()
        self.reverse = False

    def start(self, action, *args):
        source, dest = (
            (self.dest, self.source) if self.reverse else (self.source, self.dest)
        )
        return self.run(action, source, dest, *args)

    def status(self) -> Changes:
        self.use_runner(self.get_changes)
        return self.check()

    def check(self):
        return self.start("check", "--combined", "-")

    def get_changes(self, *args):
        change_results = self.generate_change_results(*args)
        changes = self.extract_changes(change_results)
        return Changes(changes)

    def extract_changes(self, change_results: Iterable[Change]):
        changes = []
        no_change_results = []
        for result in change_results:
            if result.type == ChangeType.preserved:
                no_change_results.append(result)
            else:
                changes.append(result)

        if no_change_results:
            self.update_paths_without_change(no_change_results)
        return changes

    @classmethod
    def update_paths_without_change(cls, results):
        """Update modified times to avoid checking again in future."""
        paths_without_change = [result.path for result in results]
        cls(paths=paths_without_change, quiet=False).push()

    def generate_change_results(self, *args):
        status_lines = generate_output_lines(*args)
        total = len(self.paths) if self.paths else None
        if not self.quiet:
            status_lines = cli.progress(
                status_lines,
                description="Checking",
                unit="files",
                total=total,
                cleanup=True,
            )
        for line in status_lines:
            yield Change.from_pattern(line)
