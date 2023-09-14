from dataclasses import dataclass, field

from ..utils import Path
from . import rclone


@dataclass
class Rclone(rclone.Rclone):
    folder: Path = None
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)
    path: Path = None
    sub_check_path: Path = None
    path_separator: str = field(default="/", repr=False)
    reverse: bool = False

    def __post_init__(self):
        if self.sub_check_path is not None:
            self.source /= self.sub_check_path
            self.dest /= self.sub_check_path
        if self.reverse:
            self.source, self.dest = self.dest, self.source
        super().__post_init__()

    def create_filters_path(self):
        if not self.filter_rules:
            self.create_filters()
        return super().create_filters_path()

    def create_filters(self):
        if self.folder is not None:
            self.path = self.folder / "**"
        if self.path is not None:
            self.paths = (self.path,)
        if self.paths:
            filter_rules = self.generate_path_rules()
            self.filter_rules = list(filter_rules)

    def generate_path_rules(self):
        for path in self.paths:
            source = self.dest if self.reverse else self.source
            if path.is_relative_to(source):
                path = path.relative_to(source)
            path_str = self.escape(path)
            yield f"+ /{path_str}"

        yield "- *"

    @classmethod
    def escape(cls, path: Path):
        # backslash character needs to be first in sequence
        # or otherwise each escape gets escaped again
        reserved_characters = "\\", "[", "]", "*", "**", "?", "{", "}"
        recursive_symbol = "**"
        recursive = path.name == recursive_symbol
        if recursive:
            path = path.parent
        path_str = cls.path_separator.join(path.parts)
        for character in reserved_characters:
            path_str = path_str.replace(character, f"\\{character}")
        if recursive:
            path_str += cls.path_separator + recursive_symbol

        return path_str
