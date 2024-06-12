import subprocess
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import cast

from ..models import Path
from . import syncer


@dataclass
class Backup(syncer.Backup):
    root_paths: list[Path] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.sub_check_path is not None:
            if self.sub_check_path.is_relative_to(self.source):
                self.sub_check_path = self.sub_check_path.relative_to(self.source)
            self.source /= self.sub_check_path
            self.dest /= self.sub_check_path

    def push(self, reverse: bool = False) -> subprocess.CompletedProcess[str]:
        dest = self.source if reverse else self.dest
        return (
            self.process_root_dest(reverse) if dest.is_root else super().push(reverse)
        )

    def restore_paths(self) -> None:
        self.paths = cast(list[Path], self.paths)
        # self.paths expected to be unmodified
        self.paths += self.root_paths

    def process_root_dest(self, reverse: bool) -> subprocess.CompletedProcess[str]:
        root_output = self.process_root_paths(reverse)
        output = (
            super().push()
            if self.paths
            else cast(subprocess.CompletedProcess[str], root_output)
        )
        self.restore_paths()
        return output

    def process_root_paths(
        self, reverse: bool
    ) -> subprocess.CompletedProcess[str] | None:
        root_paths = self.extract_root_paths(reverse)
        self.root_paths = list(root_paths)
        if self.root_paths or not self.paths:
            backup = syncer.Backup(
                source=self.source, dest=self.dest, root=True, paths=self.root_paths
            )
            result = backup.push(reverse=reverse)
        else:
            result = None  # pragma: nocover
        return result

    def extract_root_paths(self, reverse: bool) -> Iterator[Path]:
        self_dest = self.source if reverse else self.dest
        self.paths = list(self.paths)
        for path in self.paths:
            dest = self_dest / path
            if dest.is_root:
                self.paths.remove(path)
                yield path
