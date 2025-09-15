from collections.abc import Iterator
from dataclasses import dataclass, field

from backup import backup
from backup.context import context
from backup.models import Path
from backup.utils import parser


@dataclass
class Backup(backup.Backup):
    def __post_init__(self) -> None:
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

    @property
    def active_profile(self) -> str:
        return context.storage.active_profile.strip()
