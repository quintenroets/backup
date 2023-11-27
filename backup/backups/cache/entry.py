from dataclasses import dataclass
from typing import ClassVar

from ...utils import Path
from .raw import Backup


@dataclass
class Entry:
    source_root: Path
    dest_root: Path
    source: Path = None
    relative: Path = None
    dest: Path = None
    changed: bool = None
    include_browser: bool = None
    max_backup_size: int = 50e6
    browser_name: ClassVar[str] = "chromium"
    browser_folder: ClassVar[Path] = Path(".config") / browser_name
    browser_pattern: ClassVar[str] = f"{browser_folder}/**/*"
    relative_browser_path: ClassVar[Path] = (Path.HOME / browser_folder).relative_to(
        Backup.source
    )

    def __post_init__(self):
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(self.dest_root)
            self.source = self.source_root / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(self.source_root)
            self.dest = self.dest_root / self.relative

    def is_browser_config(self):
        return self.relative.is_relative_to(self.relative_browser_path)

    def is_changed(self):
        return (
            self.existing.is_file()
            and (self.source.mtime != self.dest.mtime)
            and not self.exclude()
        )

    def exclude(self):
        return (
            self.existing.tag
            or (not self.include_browser and self.is_browser_config())
            or (
                self.existing.size > self.max_backup_size
                and self.relative.suffix != ".zip"
            )
            or self.relative.suffix == ".part"
        )

    def get_paths(self):
        yield self.relative
