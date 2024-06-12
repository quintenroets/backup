from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import cast

from ..context import context
from ..models import Path
from . import rclone

reserved_characters = "\\", "[", "]", "*", "**", "?", "{", "}"


def calculate_sub_check_path() -> Path | None:  # pragma: no cover
    if context.options.export_resume_changes:
        sub_check_path = Path.resume
    elif context.options.sub_check:
        sub_check_path = Path.cwd()
    else:
        sub_check_path = None
    if sub_check_path is not None:
        sub_check_path = sub_check_path.relative_to(rclone.Rclone.source)
    return cast(Path | None, sub_check_path)


@dataclass
class Rclone(rclone.Rclone):
    folder: Path | None = None
    paths: list[Path] | tuple[Path] | set[Path] = field(
        default_factory=lambda: context.options.paths
    )
    path: Path | None = None
    sub_check_path: Path | None = field(default_factory=calculate_sub_check_path)
    path_separator: str = field(default="/", repr=False)

    def create_filters_path(self) -> Path:
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
            if path.is_relative_to(self.source):
                path = path.relative_to(self.source)
            path_str = self.escape(path)
            yield f"+ /{path_str}"

        if self.paths:
            yield "- *"

    @classmethod
    def escape(cls, path: Path) -> str:
        # backslash character needs to be first in sequence
        # or otherwise each escape gets escaped again
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
