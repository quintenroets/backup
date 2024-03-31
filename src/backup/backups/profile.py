from dataclasses import dataclass

from .. import backup
from ..models import Path
from ..utils import parser


@dataclass
class Backup(backup.Backup):
    source: Path = Path.HOME
    quiet: bool = True

    def __post_init__(self) -> None:
        self.set_dest(self.profile_name)
        paths = self.generate_paths()
        self.paths = list(paths)
        super().__post_init__()

    def generate_paths(self):
        rules = parser.Rules(Path.profile_paths.yaml, root=Backup.source)
        for rule in rules:
            source_path = self.source / rule.path
            dest_path = self.dest / rule.path
            is_file = source_path.is_file() or dest_path.is_file()
            if is_file:
                yield rule.path
            else:
                for path in source_path.rglob("*"):
                    yield path.relative_to(self.source)
                for path in dest_path.rglob("*"):
                    yield path.relative_to(self.dest)

    def set_dest(self, profile_name: str) -> None:
        self.dest = Path.profiles / profile_name

    @property
    def profile_name(self):
        return Path.active_profile.text.strip() or "light"

    @profile_name.setter
    def profile_name(self, value) -> None:
        Path.active_profile.text = value
        self.set_dest(value)

    def apply_profile(self, value) -> None:
        if value != self.profile_name:
            self.push()
            self.profile_name = value
            self.pull()

    def reload(self) -> None:
        self.pull()
