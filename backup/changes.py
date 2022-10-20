from dataclasses import dataclass
from enum import Enum
from typing import List

import cli


class ChangeType(Enum):
    created = "created"
    modified = "modified"
    deleted = "deleted"

    @classmethod
    @property
    def symbol_mapper(cls):
        return {
            "+": ChangeType.created,
            "*": ChangeType.modified,
            "-": ChangeType.deleted,
        }

    @classmethod
    @property
    def color_mapper(cls):
        return {"+": "green", "*": "blue", "-": "red"}

    @classmethod
    @property
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

    def __str__(self):
        return self.symbol


@dataclass
class Change:
    path: Path
    type: ChangeType

    @classmethod
    def from_pattern(cls, pattern: str):
        type_ = ChangeType.from_symbol(pattern[0])
        path = Path(pattern[2:])
        return Change(path, type_)

    @property
    def message(self):
        return f"{self.type} [bold {self.type.color}]{self.path}\n"

    def print(self):
        if self.path.parent.name != "kwalletd_hash":
            cli.console.print(self.message, end="")


@dataclass
class Changes:
    changes: List[Change]

    def __iter__(self):
        yield from self.changes

    def __bool__(self):
        return bool(self.changes)

    @property
    def paths(self):
        return [change.path for change in self.changes]

    @classmethod
    def from_patterns(cls, patterns: List[str]):
        return Changes([Change.from_pattern(pattern) for pattern in patterns])

    def print(self):
        for change in self.changes:
            change.print()
        print("")
