from collections.abc import Iterator
from dataclasses import dataclass, field

from ..context import context
from ..models import Path
from . import rclone


def calculate_sub_check_path() -> Path | None:
    if context.options.export_resume:
        sub_check_path = Path.resume
    elif context.options.subcheck:
        sub_check_path = Path.cwd()
    else:
        sub_check_path = None
    if sub_check_path is not None:
        sub_check_path = sub_check_path.relative_to(rclone.Rclone.source)
    return sub_check_path


@dataclass
class Rclone(rclone.Rclone):
    folder: Path = None
    paths: list[Path] | tuple[Path] | set[Path] = context.options.paths
    path: Path = None
    sub_check_path: Path = field(default_factory=calculate_sub_check_path)
    path_separator: str = field(default="/", repr=False)
    reverse: bool = False

    def __post_init__(self) -> None:
        if self.sub_check_path is not None:
            if self.sub_check_path.is_relative_to(self.source):
                self.sub_check_path = self.sub_check_path.relative_to(self.source)
            self.source /= self.sub_check_path
            self.dest /= self.sub_check_path
        if self.reverse:
            self.source, self.dest = self.dest, self.source
        super().__post_init__()

    @property
    def original_source(self):
        return self.dest if self.reverse else self.source

    @property
    def original_dest(self):
        return self.source if self.reverse else self.dest

    def create_filters_path(self):
        if not self.filter_rules:
            self.create_filters()
        return super().create_filters_path()

    def create_filters(self) -> None:
        if self.folder is not None:
            self.path = self.folder / "**"
        if self.path is not None:
            self.paths = (self.path,)
        filter_rules = self.generate_path_rules()
        self.filter_rules = list(filter_rules)

    def generate_path_rules(self) -> Iterator[str]:
        for path in self.paths:
            if path.is_relative_to(self.original_source):
                path = path.relative_to(self.original_source)
            path_str = self.escape(path)
            yield f"+ /{path_str}"

        if self.paths:
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
