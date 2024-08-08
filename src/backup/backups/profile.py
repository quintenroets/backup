from collections.abc import Iterator
from dataclasses import dataclass, field

from backup import backup
from backup.context import context
from backup.models import Path
from backup.utils import parser


@dataclass
class Backup(backup.Backup):
    source: Path = field(default_factory=context.extract_profiles_source_root)
    sub_check_path: Path | None = None

    def __post_init__(self) -> None:
        self.set_dest(self.active_profile)
        paths = self.generate_paths()
        self.paths = list(paths)
        super().__post_init__()

    def generate_path_rules(self) -> Iterator[str]:
        if not self.paths:
            yield "- *"
        yield from super().generate_path_rules()

    def generate_paths(self) -> Iterator[Path]:
        rules = parser.Rules(
            context.storage.profile_paths,
            root=context.extract_profiles_source_root(),
        )
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
        self.dest = context.profiles_path / profile_name
        self.dest.mkdir(parents=True, exist_ok=True)
        self.filter_rules = []

    @property
    def active_profile(self) -> str:
        return context.storage.active_profile.strip()

    @active_profile.setter
    def active_profile(self, value: str) -> None:
        context.storage.active_profile = value
        self.set_dest(value)

    def apply_profile(self, value: str) -> None:
        if value != self.active_profile:
            self.push()
            self.active_profile = value
            self.pull()

    def reload(self) -> None:
        self.pull()
