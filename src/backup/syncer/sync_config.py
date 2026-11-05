from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field

from cli.commands.commands import CommandItem
from superpathlib import Path


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    options: list[CommandItem] = field(default_factory=list)
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)
    path: Path | None = None
    directory: Path | None = None

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
