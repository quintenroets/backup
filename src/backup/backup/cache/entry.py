from collections.abc import Iterator
from collections.abc import Iterator
from dataclasses import dataclass, field

from backup.context import context
from backup.models import Path

from . import entry
from .checkers.detailed import Checker
from .checkers.path import extract_hash_path
from dataclasses import dataclass, field
from typing import ClassVar

from backup.context import context
from backup.models import Path

from backup.backup.config import BackupConfig


@dataclass
class Entry:
    config: BackupConfig
    source: Path = None  # type: ignore[assignment]
    dest: Path = None  # type: ignore[assignment]
    existing: Path = field(init=False)
    relative: Path = field(init=False)
    changed: bool | None = None
    hash_path: Path | None = None

    def __post_init__(self) -> None:
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(self.config.cache)
            self.source = self.config.source / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(self.config.source)
            self.dest = self.config.cache / self.relative

    def is_browser_config(self) -> bool:
        return self.relative.is_relative_to(context.config.browser_folder)

    def is_changed(self) -> bool:
        return (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )

    def exclude(self) -> bool:
        return (
            (not context.options.include_browser and self.is_browser_config())
            or (self.existing.tag and self.existing.tag == "exported")
            or (
                self.existing.size > context.config.max_backup_size
                and self.relative.suffix != ".zip"
            )
            or self.relative.suffix == ".part"
            or self.only_volatile_content_changed()
        )

    def only_volatile_content_changed(self) -> bool:
        only_volatile_content_changed = (
            self.relative in Checker.checkers and self.relevant_content_unchanged()
        )
        if only_volatile_content_changed:
            self.update_cached_dest()
        else:
            hash_path = extract_hash_path(self.source, self.config)
            if hash_path.exists():
                self.hash_path = hash_path.relative_to(self.config.source)
        return only_volatile_content_changed

    def relevant_content_unchanged(self) -> bool:
        checker = Checker.checkers[self.relative]
        source_hash = checker.calculate_relevant_hash(self.source, self.config)
        dest_hash = checker.calculate_relevant_hash(self.dest, self.config)
        return source_hash == dest_hash

    def update_cached_dest(self) -> None:
        no_original_mtime_present = (
            self.dest.exists()
            and self.dest.is_relative_to(self.config.cache)
            and self.dest.tag is None
        )
        if no_original_mtime_present:
            self.dest.tag = str(self.dest.mtime)
        self.source.copy_to(self.dest, include_properties=False)
        self.dest.touch(mtime=self.source.mtime)

    def get_paths(self) -> Iterator[Path]:
        yield self.relative
        if self.hash_path is not None:
            yield self.hash_path

    def __hash__(self) -> int:
        return hash(self.relative)
