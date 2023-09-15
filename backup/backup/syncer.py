from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime

import cli

from ..utils import Path
from . import commands


@dataclass
class Backup(commands.Backup):
    date_start: str = "── ["
    date_end: str = "]  /"

    def tree(self, path=None):
        if path is None:
            path = self.dest
        self.use_runner(cli.lines)
        args = "tree", "--all", "--modtime", "--noreport", "--full-path", path
        return self.run(*args)

    def get_dest_info(self):
        tree = self.tree()
        for line in tree:
            contains_date = self.date_start in line
            if contains_date:
                info = line.split(self.date_start)[1]
                date_str, path_str = info.split(self.date_end)
                date = datetime.strptime(date_str, "%b %d %H:%M")
                path = Path(path_str)
                yield path, date

    def update_dest(self, dest_info):
        dest_files = self.process_dest_info(dest_info)
        self.delete_missing(dest_files)

    def delete_missing(self, to_keep: Iterable[Path]):
        to_keep = set(to_keep)
        dest_info = self.get_dest_info()
        for path, _ in dest_info:
            if path not in to_keep:
                dest_path = self.dest / path
                dest_path.unlink()

    def process_dest_info(self, dest_info):
        for relative_path, date in dest_info:
            path = self.dest / relative_path
            changed = not path.exists() or not path.has_date(date)
            if changed:
                changed = not path.has_date(date, check_tag=True)
            if changed:
                self.change_path(path)
            yield relative_path

    def change_path(self, path: Path):
        # change content and mtime trigger update
        source_path = self.source / path.relative_to(self.dest)
        path.text = "" if source_path.size else " "
        path.touch(mtime=path.mtime + 1)
