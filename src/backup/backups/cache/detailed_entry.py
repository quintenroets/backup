from collections.abc import Iterator
from dataclasses import dataclass, field

from backup.context import context
from backup.models import Path

from . import entry
from .checker.detailed import Checker
from .checker.path import extract_hash_path


@dataclass
class Entry(entry.Entry):
    hash_path: Path | None = field(default=None, hash=False)

    def exclude(self) -> bool:
        return super().exclude() or self.only_volatile_content_changed()

    def only_volatile_content_changed(self) -> bool:
        only_volatile_content_changed = (
            self.check_key in Checker.checkers and self.relevant_content_unchanged()
        )
        if only_volatile_content_changed:
            self.update_cached_dest()
        else:
            hash_path = extract_hash_path(self.source)
            if hash_path.exists():
                self.hash_path = hash_path.relative_to(context.config.backup_source)
        return only_volatile_content_changed

    def relevant_content_unchanged(self) -> bool:
        checker = Checker.checkers[self.check_key]
        source_hash = checker.calculate_relevant_hash(self.source)
        dest_hash = checker.calculate_relevant_hash(self.dest)
        return source_hash == dest_hash

    def update_cached_dest(self) -> None:
        no_original_mtime_present = (
            self.dest.exists()
            and self.dest.is_relative_to(context.config.cache_path)
            and self.dest.tag is None
        )
        if no_original_mtime_present:
            self.dest.tag = str(self.dest.mtime)
        self.source.copy_to(self.dest, include_properties=False)
        self.dest.touch(mtime=self.source.mtime)

    @property
    def check_key(self) -> Path:
        if self.source.is_relative_to(context.profiles_path):
            check_key = self.source.relative_to(context.profiles_path)
            check_key = check_key.relative_to(check_key.parts[0])
        elif self.source.is_relative_to(context.profiles_source_root):
            check_key = self.source.relative_to(context.profiles_source_root)
        else:
            check_key = self.relative
        return check_key

    def get_paths(self) -> Iterator[Path]:
        yield from super().get_paths()
        if self.hash_path is not None:
            yield self.hash_path

    def __hash__(self) -> int:
        return hash(self.relative)
