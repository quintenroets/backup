from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import datetime, timezone

from backup.models import Path

from . import commands


@dataclass
class Backup(commands.Backup):
    date_start: str = "── ["
    date_end: str = "]  /"

    def tree(self, path: Path | None = None) -> list[str]:
        if path is None:
            path = self.dest
        options = "lsl", path
        with self.prepared_runner(options) as runner:
            output = runner.capture_output()
        return [line for line in output.splitlines() if line]

    def get_dest_info(self) -> Iterator[tuple[Path, datetime]]:
        tree = self.tree()
        for line in tree:
            parts = line.split()
            date_str = " ".join(parts[1:3]).split(".")[0]
            path_str = " ".join(parts[3:])
            if path_str:
                date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S").astimezone(
                    tz=timezone.utc,
                )
                path = Path(path_str)
                yield path, date

    def update_dest(self, dest_info: Iterator[tuple[Path, datetime]]) -> None:
        dest_files = self.process_dest_info(dest_info)
        self.delete_missing(dest_files)

    def delete_missing(self, to_keep: Iterable[Path]) -> None:
        to_keep = set(to_keep)
        dest_info = self.get_dest_info()
        for path, _ in dest_info:
            if path not in to_keep:
                dest_path = self.dest / path
                dest_path.unlink()

    def process_dest_info(
        self,
        dest_info: Iterator[tuple[Path, datetime]],
    ) -> Iterator[Path]:
        for relative_path, date in dest_info:
            path = self.dest / relative_path
            changed = not path.exists() or not path.has_date(date)
            if changed:
                changed = not path.has_date(date, check_tag=True)
            if changed:
                self.change_path(path)
            yield relative_path

    def change_path(self, path: Path) -> None:
        # change content and mtime trigger update
        source_path = self.source / path.relative_to(self.dest)
        path.text = "" if source_path.size else " "
        path.touch(mtime=path.mtime + 1)
