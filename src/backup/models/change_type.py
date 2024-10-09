from __future__ import annotations

from dataclasses import dataclass

from typing_extensions import Self


@dataclass(frozen=True)
class ChangeType:
    color: str
    symbol: str

    def __str__(self) -> str:
        return self.symbol

    @property
    def sort_order(self) -> int:
        return symbols.index(self.symbol)

    def __lt__(self, other: Self) -> bool:
        return self.sort_order.__lt__(other.sort_order)


class ChangeTypes:
    created = ChangeType("green", "+")
    modified = ChangeType("blue", "*")
    deleted = ChangeType("red", "-")
    preserved = ChangeType("black", "=")


symbol_to_change_type: dict[str, ChangeType] = {
    change_type.symbol: change_type
    for name, change_type in ChangeTypes.__dict__.items()
    if not name.startswith("_")
}
symbols = list(symbol_to_change_type.keys())


def parse_change_type(symbol: str) -> ChangeType:
    return symbol_to_change_type[symbol]
