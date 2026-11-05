from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Self

from superpathlib import Path


class ChangeType(Enum):
    created = "green", "+"
    modified = "blue", "*"
    deleted = "red", "-"
    preserved = "black", "="

    def __init__(self, color: str, symbol: str) -> None:
        self.color = color
        self.symbol = symbol


@dataclass(unsafe_hash=True)
class Change:
    path: Path
    type: ChangeType = ChangeType.created
    source: Path | None = None
    dest: Path | None = None

    @classmethod
    def from_pattern(
        cls,
        pattern: str,
        source: Path | None = None,
        dest: Path | None = None,
    ) -> Self:
        type_ = {member.symbol: member for member in ChangeType}[pattern[0]]
        path = Path(pattern[2:])
        return cls(path, type_, source, dest)


Changes = list[Change]
