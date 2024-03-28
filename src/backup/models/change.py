from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import cli
from simple_classproperty import classproperty

from ..utils import differ
from .path import Path


class ChangeType(Enum):
    created = "created"
    modified = "modified"
    deleted = "deleted"
    preserved = "preserved"

    @classmethod
    @classproperty
    def symbol_mapper(cls):
        return {
            "+": ChangeType.created,
            "*": ChangeType.modified,
            "-": ChangeType.deleted,
            "=": ChangeType.preserved,
        }

    @classmethod
    @classproperty
    def color_mapper(cls):
        return {"+": "green", "*": "blue", "-": "red", "=": "black"}

    @classmethod
    @classproperty
    def reverse_symbol_mapper(cls):
        return {v: k for k, v in cls.symbol_mapper.items()}

    @classmethod
    def from_symbol(cls, symbol: str):
        return cls.symbol_mapper[symbol]

    @property
    def color(self):
        return self.color_mapper[self.symbol]

    @property
    def symbol(self):
        return self.reverse_symbol_mapper[self]

    def __str__(self) -> str:
        return self.symbol

    @property
    def sort_order(self):
        symbols = list(self.symbol_mapper.keys())
        return symbols.index(self.symbol)

    def __lt__(self, other):
        return self.sort_order.__lt__(other.sort_order)


@dataclass
class Change:
    path: Path
    type: ChangeType
    source: Path = None
    dest: Path = None
    max_diff_lines_per_file: int = 20

    @classmethod
    def from_pattern(cls, pattern: str, source: Path = None, dest: Path = None):
        type_ = ChangeType.from_symbol(pattern[0])
        path = Path(pattern[2:])
        return Change(path, type_, source, dest)

    @property
    def message(self) -> str:
        return f"{self.type} [bold {self.type.color}]{self.path}\n"

    @property
    def sort_index(self):
        return self.type, self.path

    @property
    def skip_print(self):
        return (self.source / self.path).is_relative_to(Path.hashes)  # noqa

    def print(self) -> None:
        cli.console.print(self.message, end="")

    def get_diff_lines(self, color: bool = True):
        max_lines = self.max_diff_lines_per_file
        return differ.get_diff(
            self.path, self.source, self.dest, color=color, max_lines=max_lines
        )
