from collections.abc import Iterable
from dataclasses import dataclass

import cli

from ..utils import Change, Changes, ChangeType, Path, generate_output_lines
from . import paths


@dataclass
class Backup(paths.Rclone):
    def compare(self):
        return self.status()

    def status(self) -> Changes:
        self.use_runner(self.get_changes)
        return self.check()

    def check(self):
        return self.start("check", "--combined", "-")

    def push(self):
        return self.start("sync", "--create-empty-src-dirs", "--progress")

    def pull(self):
        backup = Backup(
            paths=self.paths,
            path=self.path,
            folder=self.folder,
            source=self.source,
            dest=self.dest,
            quiet=self.quiet,
            reverse=True,
        )
        return backup.push()

    def start(self, action, *args):
        return self.run(action, self.source, self.dest, *args)

    def get_changes(self, *args, **kwargs):
        change_results = self.generate_change_results(*args, **kwargs)
        changes = self.extract_changes(change_results)
        changes = list(changes)
        return Changes(changes)

    def extract_changes(self, change_results: Iterable[Change]):
        no_change_results = []
        for result in change_results:
            if result.type == ChangeType.preserved:
                no_change_results.append(result)
            else:
                yield result

        if no_change_results:
            self.update_paths_without_change(no_change_results)

    def update_paths_without_change(self, results):
        """
        Update modified times to avoid checking again in the future.
        """
        no_change_paths = [result.path for result in results]
        if self.dest.is_relative_to(Path.backup_cache):  # noqa
            for path in no_change_paths:
                dest = self.dest / path
                if dest.tag is None:
                    dest.tag = dest.mtime  # save original mtime for remote syncing

        backup = Backup(
            source=self.source,
            dest=self.dest,
            paths=no_change_paths,
            quiet=True,
        )
        backup.push()

    def generate_change_results(self, *args, **kwargs):
        status_lines = generate_output_lines(*args, **kwargs)
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
            yield Change.from_pattern(line, self.source, self.dest)
