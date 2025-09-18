from collections.abc import Iterable
from typing import Iterator
from dataclasses import dataclass, field

from cli.commands.commands import CommandItem

from backup.models import Path


@dataclass
class SyncConfig:
    source: Path = Path.backup_source
    dest: Path = Path.remote
    sub_check_path: Path | None = None
    options: list[CommandItem] = field(default_factory=list)
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)
    path: Path | None = None
    directory: Path | None = None

    def __post_init__(self):
        if self.sub_check_path is not None:
            sub_check_path = self.sub_check_path
            if sub_check_path.is_relative_to(self.source):
                sub_check_path = sub_check_path.relative_to(self.source)
            self.source /= sub_check_path
            self.dest /= sub_check_path

    @property
    def overlapping_sub_path(self) -> Path | None:
        return next(self.generate_overlapping_sub_paths(), None)

    def generate_overlapping_sub_paths(self) -> Iterator[Path]:
        pairs = [(self.source, self.dest), (self.dest, self.source)]
        for first, second in pairs:
            if first.is_relative_to(second):
                path = first.relative_to(second)
                while path.name == second.name:
                    path = path.parent
                    second = second.parent
                yield path

    def with_paths(self, paths: Iterable[Path]) -> "SyncConfig":
        return SyncConfig(
            source=self.source,
            dest=self.dest,
            sub_check_path=self.sub_check_path,
            options=self.options,
            paths=list(paths),
        )

    def with_dest_root(self, dest: Path) -> "SyncConfig":
        return SyncConfig(
            source=self.source,
            dest=dest / self.dest,
            sub_check_path=self.sub_check_path,
            options=self.options,
            paths=self.paths,
        )
