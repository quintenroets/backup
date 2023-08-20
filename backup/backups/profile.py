from dataclasses import dataclass

from .. import backup
from ..utils import Path


@dataclass
class Backup(backup.Backup):
    quiet: bool = True

    def __post_init__(self):
        self.paths = Path.profile_paths.parsed_paths
        super().__post_init__()
        self.set_dest(self.profile_name)

    def set_dest(self, profile_name: str):
        self.dest = Path.profiles / profile_name

    @property
    def profile_name(self):
        return Path.active_profile.text.strip() or "light"

    @profile_name.setter
    def profile_name(self, value):
        Path.active_profile.text = value
        self.set_dest(value)

    def apply_profile(self, value):
        if value != self.profile_name:
            self.copy()
            self.profile_name = value
            self.pull()

    def reload(self):
        if Path.active_profile.exists():
            self.pull()

    def pull(self):
        self.reverse = True
        self.copy()
