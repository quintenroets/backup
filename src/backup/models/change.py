from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, cast

import cli
from simple_classproperty import classproperty
from typing_extensions import Self

from .path import Path


class ChangeType(Enum):
    created = "created"
    modified = "modified"
    deleted = "deleted"
    preserved = "preserved"

    @classmethod
    @classproperty
    def symbol_mapper(cls) -> dict[str, ChangeType]:
        return {
            "+": cls.created,
            "*": cls.modified,
            "-": cls.deleted,
            "=": cls.preserved,
        }

    @classmethod
    @classproperty
    def color_mapper(cls) -> dict[str, str]:
        return {"+": "green", "*": "blue", "-": "red", "=": "black"}

    @classmethod
    @classproperty
    def reverse_symbol_mapper(cls) -> dict[str, str]:
        return {v: k for k, v in cls.symbol_mapper.items()}

    @classmethod
    def from_symbol(cls, symbol: str) -> Self:
        change_type = cls.symbol_mapper[symbol]
        return cast(Self, change_type)

    @property
    def color(self) -> str:
        color = self.color_mapper[self.symbol]
        return cast(str, color)

    @property
    def symbol(self) -> str:
        symbol = self.reverse_symbol_mapper[self]
        return cast(str, symbol)

    def __str__(self) -> str:
        return self.symbol

    @property
    def sort_order(self) -> int:
        symbols = list(self.symbol_mapper.keys())
        return symbols.index(self.symbol)

    def __lt__(self, other: Self) -> bool:
        return self.sort_order.__lt__(other.sort_order)


@dataclass
class Change:
    path: Path
    type: ChangeType = ChangeType.created
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
        type_ = ChangeType.from_symbol(pattern[0])
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
        source = cast(Path, self.source)
        return (source / self.path).is_relative_to(Path.hashes)

    def print(self) -> None:
        cli.console.print(self.message, end="")

    def get_diff_lines(self, *, color: bool = True) -> list[str]:
        max_lines = self.max_diff_lines_per_file
        source = cast(Path, self.source)
        dest = cast(Path, self.dest)
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
