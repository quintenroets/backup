from dataclasses import dataclass, field
from typing import Iterable

from cli.commands.commands import CommandItem

from backup.context import context
from backup.models import Path


@dataclass
class RcloneConfig:
    source: Path = field(default_factory=context.extract_backup_source)
    dest: Path = field(default_factory=context.extract_backup_dest)
    sub_check_path: Path | None = field(default_factory=lambda: context.sub_check_path)
    options: list[CommandItem] = field(default_factory=list)
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] | tuple[Path] | set[Path] = field(
        default_factory=lambda: context.options.paths,
    )
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
        if self.dest.is_relative_to(self.source):
            path = self.dest.relative_to(self.source)
        elif self.source.is_relative_to(self.dest):
            path = self.source.relative_to(self.dest)
        else:
            path = None
        return path

    def with_paths(self, paths: Iterable[Path]) -> "RcloneConfig":
        return RcloneConfig(
            source=self.source,
            dest=self.dest,
            sub_check_path=self.sub_check_path,
            options=self.options,
            paths=list(paths),
        )

    def with_dest_root(self, dest: Path) -> "RcloneConfig":
        return RcloneConfig(
            source=self.source,
            dest=dest / self.dest,
            sub_check_path=self.sub_check_path,
            options=self.options,
            paths=self.paths,
        )
