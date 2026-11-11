from collections.abc import Iterator
from dataclasses import dataclass, field

from superpathlib import Path

from .sync_config import SyncConfig

reserved_characters = "\\", "[", "]", "*", "?", "{", "}"


@dataclass
class FiltersCreator:
    config: SyncConfig
    path_separator: str = field(default="/", repr=False)

    def create_filters_from_paths(self) -> None:
        self.config.filter_rules = list(self.generate_filters_from_paths())

    def generate_filters_from_paths(self) -> Iterator[str]:
        for path in self.config.paths:
            relative_path = (
                path.relative_to(self.config.source)
                if path.is_relative_to(self.config.source)
                else path
            )
            path_str = self.escape(relative_path)
            yield f"+ /{path_str}"
            yield f"+ /{path_str}/**"

        if self.config.paths:
            yield "- *"

    def escape(self, path: Path) -> str:
        # backslash character needs to be first in sequence
        # or otherwise each escape gets escaped again
        path_str = self.path_separator.join(path.parts)
        for character in reserved_characters:
            path_str = path_str.replace(character, f"\\{character}")
        return path_str
