from __future__ import annotations

import functools
from enum import Enum
from typing import cast

from typing_extensions import Self


class ChangeType(Enum):
    created = "created"
    modified = "modified"
    deleted = "deleted"
    preserved = "preserved"

    @classmethod
    @functools.cache
    def symbol_mapper(cls) -> dict[str, ChangeType]:
        return {
            "+": cls.created,
            "*": cls.modified,
            "-": cls.deleted,
            "=": cls.preserved,
        }

    @classmethod
    @functools.cache
    def color_mapper(cls) -> dict[str, str]:
        return {"+": "green", "*": "blue", "-": "red", "=": "black"}

    @classmethod
    @functools.cache
    def reverse_symbol_mapper(cls) -> dict[ChangeType, str]:
        return {v: k for k, v in cls.symbol_mapper().items()}

    @classmethod
    def from_symbol(cls, symbol: str) -> Self:
        change_type = cls.symbol_mapper()[symbol]
        return cast(Self, change_type)

    @property
    def color(self) -> str:
        return self.color_mapper()[self.symbol]

    @property
    def symbol(self) -> str:
        return self.reverse_symbol_mapper()[self]

    def __str__(self) -> str:
        return self.symbol

    @property
    def sort_order(self) -> int:
        symbols = list(self.symbol_mapper().keys())
        return symbols.index(self.symbol)

    def __lt__(self, other: Self) -> bool:
        return self.sort_order.__lt__(other.sort_order)
