from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from cli.commands.commands import CommandItem
from superpathlib import Path

from backup.models import Path as BackupPath


@dataclass
class SyncConfig:
    source: Path = BackupPath.backup_source
    dest: Path = BackupPath.remote
    sub_check_path: Path | None = None
    options: list[CommandItem] = field(default_factory=list)
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)
    path: Path | None = None
    directory: Path | None = None

    def __post_init__(self) -> None:
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
        yield from generate_overlapping_sub_path(self.source, self.dest)
        yield from generate_overlapping_sub_path(self.dest, self.source)

    def with_paths(self, paths: Iterable[Path]) -> "SyncConfig":
        return SyncConfig(
            source=self.source,
            dest=self.dest,
            sub_check_path=self.sub_check_path,
            options=self.options,
            paths=list(paths),
        )


def generate_overlapping_sub_path(source: Path, dest: Path) -> Iterator[Path]:
    if source.is_relative_to(dest):
        path = source.relative_to(dest)
        while path.name == dest.name:
            path = path.parent
            dest = dest.parent
        yield path
