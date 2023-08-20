from dataclasses import dataclass, field

from ..utils import Path
from . import rclone


@dataclass
class Rclone(rclone.Rclone):
    folder: Path = None
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)

    def create_filters_path(self):
        if not self.filter_rules:
            self.create_filters()
        return super().create_filters_path()

    def create_filters(self):
        if self.folder is not None:
            self.paths = (self.folder / "**",)
        if self.paths:
            filter_rules = self.generate_path_rules()
            self.filter_rules = list(filter_rules)

    def generate_path_rules(self):
        for path in self.paths:
            if path.is_absolute():
                path = path.relative_to(self.source)
            path_str = self.escape(path)
            yield f"+ /{path_str}"

        yield "- *"

    @classmethod
    def escape(cls, path: Path):
        # backslash character needs to be first in sequence
        # or otherwise each escape gets escaped again
        reserved_characters = "\\", "[", "]", "*", "**", "?", "{", "}"
        path = str(path)
        for character in reserved_characters:
            path = path.replace(character, f"\\{character}")
        return path
