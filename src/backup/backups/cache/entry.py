import typing
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar

from backup.context import context
from backup.models import Path


@dataclass
class Entry:
    source_root: Path
    dest_root: Path
    source: Path = None  # type: ignore[assignment]
    existing: Path = field(init=False)
    relative: Path = field(init=False)
    dest: Path = None  # type: ignore[assignment]
    changed: bool | None = None
    relative_browser_path: ClassVar[Path] = (
        Path.HOME / context.config.browser_folder
    ).relative_to(context.config.backup_source)

    def __post_init__(self) -> None:
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(self.dest_root)
            self.source = self.source_root / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(self.source_root)
            self.dest = self.dest_root / self.relative

    def is_browser_config(self) -> bool:
        return self.relative.is_relative_to(self.relative_browser_path)

    def is_changed(self) -> bool:
        return (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )

    def exclude(self) -> bool:
        return (
            (not context.options.include_browser and self.is_browser_config())
            or typing.cast(bool, self.existing.tag)
            or (
                self.existing.size > context.config.max_backup_size
                and self.relative.suffix != ".zip"
            )
            or self.relative.suffix == ".part"
        )

    def get_paths(self) -> Iterator[Path]:
        yield self.relative
