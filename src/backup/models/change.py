from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import cli
from typing_extensions import Self

from .change_type import ChangeType, ChangeTypes, parse_change_type
from .path import Path


@dataclass(unsafe_hash=True)
class Change:
    path: Path
    type: ChangeType = ChangeTypes.created
    source: Path | None = None
    dest: Path | None = None
    max_diff_lines_per_file: int = 20

    @classmethod
    def from_pattern(
        cls,
        pattern: str,
        source: Path | None = None,
        dest: Path | None = None,
    ) -> Self:
        type_ = parse_change_type(symbol=pattern[0])
        path = Path(pattern[2:])
        return cls(path, type_, source, dest)

    @property
    def message(self) -> str:
        return f"{self.type} [bold {self.type.color}]{self.path}\n"

    @property
    def sort_index(self) -> tuple[ChangeType, Path]:
        return self.type, self.path

    @property
    def skip_print(self) -> bool:
        source = cast("Path", self.source)
        return (source / self.path).is_relative_to(Path.hashes)

    def print(self) -> None:
        cli.console.print(self.message, end="")

    def get_diff_lines(self, *, color: bool = True) -> list[str]:
        max_lines = self.max_diff_lines_per_file
        source = cast("Path", self.source)
        dest = cast("Path", self.dest)
        return calculate_diff(self.path, source, dest, color=color, max_lines=max_lines)


def calculate_diff(
    path: Path,
    source_root: Path,
    dest_root: Path,
    *,
    color: bool = True,
    max_lines: int = 20,
) -> list[str]:
    source = source_root / path
    dest = dest_root / path
    diff_command: tuple[str | Path, ...] = ("diff", "-u", "--new-file", dest, source)
    if color:
        diff_command = *diff_command, "--color=always"
    return cli.capture_output_lines(*diff_command, check=False)[2 : 2 + max_lines]


def run_diff(*args: Any, **kwargs: Any) -> None:
    diff_lines = calculate_diff(*args, **kwargs)
    message = "\n".join(diff_lines)
    cli.console.print(message)
