from dataclasses import dataclass

import cli

from .. import backup
from ..utils import Path
from ..utils.custom_checker import custom_checkers as checkers
from . import cache_to_remote


@dataclass
class PathEntry:
    source: Path = None
    relative: Path = None
    dest: Path = None
    changed: bool = None
    include_browser: bool = None
    max_backup_size: int = 50e6
    browser_name: str = "chromium"
    browser_folder: Path = Path(".config") / browser_name
    browser_pattern: str = f"{browser_folder}/**/*"

    def __post_init__(self):
        if self.source is None:
            self.existing = self.dest
            self.relative = self.dest.relative_to(Backup.dest)
            self.source = Backup.source / self.relative
        else:
            self.existing = self.source
            self.relative = self.source.relative_to(Backup.source)
            self.dest = Backup.dest / self.relative

    def is_browser_config(self):
        return self.relative.is_relative_to(self.browser_folder)

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


@dataclass
class Backup(backup.Backup):
    quiet: bool = True
    dest: Path = Path.backup_cache

    def __post_init__(self):
        if not self.dest.exists():
            self.create_dest()
        super().__post_init__()

    def create_dest(self):
        commands = (f"mkdir {self.dest}", f"chown -R $(whoami):$(whoami) {self.dest}")
        cli.sh(*commands, root=True)
        cache_to_remote.Backup().pull()
