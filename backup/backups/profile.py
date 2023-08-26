from dataclasses import dataclass

from .. import backup
from ..utils import Path, parser


@dataclass
class Backup(backup.Backup):
    source: Path = Path.HOME
    quiet: bool = True

    def __post_init__(self):
        rules = parser.Rules(Path.profile_paths.yaml, root=Path.HOME)  # noqa
        self.paths = rules.get_paths()
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
