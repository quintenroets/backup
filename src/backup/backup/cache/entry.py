from dataclasses import dataclass, field

from backup.context import context
from backup.models import BackupConfig, Path


@dataclass
class Entry:
    config: BackupConfig
    source: Path = None  # type: ignore[assignment]
    dest: Path = None  # type: ignore[assignment]
    existing: Path = field(init=False)
    relative: Path = field(init=False)

    def __post_init__(self) -> None:
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(self.config.cache)
            self.source = self.config.source / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(self.config.source)
            self.dest = self.config.cache / self.relative

    def is_changed(self) -> bool:
        return (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )

    def exclude(self) -> bool:
        return (
            (self.existing.tag and self.existing.tag == "exported")
            or (
                self.existing.size > context.config.max_backup_size
                and self.relative.suffix != ".zip"
            )
            or self.relative.suffix == ".part"
        )

    def __hash__(self) -> int:
        return hash(self.relative)
