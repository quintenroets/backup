from dataclasses import dataclass, field

from superpathlib import Path

from backup.context import context
from backup.models import Backup


@dataclass
class Entry:
    backup: Backup
    source: Path = None  # type: ignore[assignment]
    dest: Path = None  # type: ignore[assignment]
    existing: Path = field(init=False)
    relative: Path = field(init=False)

    def __post_init__(self) -> None:
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(self.backup.cache)
            self.source = self.backup.source / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(self.backup.source)
            self.dest = self.backup.cache / self.relative

    def is_changed(self) -> bool:
        return (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )

    def exclude(self) -> bool:
        return self.relative.suffix == ".part" or (
            self.existing.size > context.config.max_backup_size
            and self.relative.suffix != ".zip"
        )
