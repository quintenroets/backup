from dataclasses import dataclass, field

from ...utils import Path
from . import entry
from .checker.detailed import Checker
from .raw import Backup


@dataclass
class Entry(entry.Entry):
    hash_path: Path = field(default=None, hash=False)

    def exclude(self):
        return super().exclude() or self.only_volatile_content_changed()

    def only_volatile_content_changed(self) -> bool:
        if self.check_key in Checker.checkers:
            checker = Checker.checkers[self.check_key]
            source_hash = checker.calculate_relevant_hash(self.source)
            dest_hash = checker.calculate_relevant_hash(self.dest)
            only_volatile_content_changed = source_hash == dest_hash
        else:
            only_volatile_content_changed = False

        if only_volatile_content_changed:
            self.update_cached_dest()
        elif self.source.hash_path.exists():
            self.hash_path = self.source.hash_path.relative_to(Backup.source)
        return only_volatile_content_changed

    def update_cached_dest(self):
        no_original_mtime_present = (
            self.dest.exists()
            and self.dest.is_relative_to(Path.backup_cache)
            and self.dest.tag is None
        )
        if no_original_mtime_present:
            self.dest.tag = self.dest.mtime
        self.source.copy_to(self.dest, include_properties=False)
        self.dest.touch(mtime=self.source.mtime)

    @property
    def check_key(self):
        if self.source.is_relative_to(Path.profiles):
            check_key = self.source.relative_to(Path.profiles)
            check_key = check_key.relative_to(check_key.parts[0])
        elif self.source.is_relative_to(Path.HOME):  # noqa
            check_key = self.source.relative_to(Path.HOME)  # noqa
        else:
            check_key = self.relative
        return check_key

    def get_paths(self):
        yield from super().get_paths()
        if self.hash_path is not None:
            yield self.hash_path

    def __hash__(self):
        return hash(self.relative)
