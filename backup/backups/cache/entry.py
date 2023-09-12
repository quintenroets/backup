from dataclasses import dataclass, field

from ...utils import Path, custom_checker
from .raw import Backup

checkers = custom_checker.custom_checkers


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
    browser_name: str = field(default="chromium", repr=False)
    browser_folder: Path = field(
        default=Path(".config") / browser_name.default, repr=False  # noqa
    )
    browser_pattern: str = field(
        default=f"{browser_folder.default}/**/*", repr=False  # noqa
    )
    relative_browser_path: Path = field(
        default=(Path.HOME / browser_folder.default).relative_to(Backup.source),
        repr=False,
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

    def __hash__(self):
        return hash(self.relative)

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
        checker = checkers.get(self.check_key)
        if checker:
            if checker(self.source) == checker(self.dest):
                self.dest.touch(mtime=self.source.mtime)
            else:
                yield self.relative
                if self.source.hash_path.exists():
                    yield self.source.hash_path.relative_to(Backup.source)
        else:
            yield self.relative
