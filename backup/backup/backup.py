from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

import cli

from ..utils import Change, Changes, ChangeType, Path, generate_output_lines
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
        self.push()
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

    def get_changes(self, *args, **kwargs):
        change_results = self.generate_change_results(*args, **kwargs)
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
        """
        Update modified times to avoid checking again in the future.
        """
        paths_without_change = [result.path for result in results]
        cls(paths=paths_without_change, quiet=True).push()

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
            yield Change.from_pattern(line)

    def tree(self, path=None):
        if path is None:
            path = self.dest
        self.use_runner(cli.lines)
        args = "tree", "--all", "--modtime", "--noreport", "--full-path", path
        return self.run(*args)

    def get_dest_info(self, message: str | None = "Getting remote info"):
        if message is None:
            tree = self.tree()
        else:
            with cli.status(message):
                tree = self.tree()
        yield from self.parse_tree(tree)

    @classmethod
    def parse_tree(cls, tree: list[str]):
        date_start = "── ["
        date_end = "]  /"

        for line in tree:
            contains_date = date_start in line
            if contains_date:
                date_str, path_str = line.split(date_start)[1].split(date_end)
                date = datetime.strptime(date_str, "%b %d %H:%M")
                path = Path(path_str)
                yield path, date

    def update_dest(self, dest_info):
        dest_files = self.process_dest_info(dest_info)
        self.delete_missing(dest_files)

    def delete_missing(self, to_keep: Iterable[Path]):
        to_keep = set(to_keep)
        dest_info = self.get_dest_info(message=None)
        for path, _ in dest_info:
            if path not in to_keep:
                dest_path = self.dest / path
                dest_path.unlink()

    def process_dest_info(self, dest_info):
        for relative_path, date in dest_info:
            path = self.dest / relative_path
            changed = not path.exists() or not path.has_date(date)
            if changed:
                self.change_path(path)
            yield relative_path

    def change_path(self, path: Path):
        # change content and mtime trigger update
        source_path = self.source / path.relative_to(self.dest)
        path.text = "" if source_path.size else " "
        path.touch(mtime=path.mtime + 1)
