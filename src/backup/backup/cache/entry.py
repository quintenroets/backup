from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import cast

from backup.context import context
from backup.models import BackupConfig, Path


def extract_hash_path(path: Path, config: BackupConfig) -> Path:
    root = config.cache if path.is_relative_to(config.cache) else config.source
    return cast("Path", root / Path.hashes.relative_to(config.source) / path.name)


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

    def is_changed(self) -> bool:
        changed = (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )
        if changed:
            self.assign_hash_path()
        return changed

    def exclude(self) -> bool:
        return (
            (self.existing.tag and self.existing.tag == "exported")
            or (
                self.existing.size > context.config.max_backup_size
                and self.relative.suffix != ".zip"
            )
            or self.relative.suffix == ".part"
        )

    def assign_hash_path(self) -> None:
        if Path.hashes.is_relative_to(self.config.source):
            hash_path = extract_hash_path(self.source, self.config)
            if hash_path.exists():
                self.hash_path = hash_path.relative_to(self.config.source)

    def get_paths(self) -> Iterator[Path]:
        yield self.relative
        if self.hash_path is not None:
            yield self.hash_path

    def __hash__(self) -> int:
        return hash(self.relative)
