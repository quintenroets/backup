from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Self, cast

import cli
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
    max_diff_lines_per_file: int = 20

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

    def get_diff_lines(self, *, color: bool = True) -> list[str]:
        max_lines = self.max_diff_lines_per_file
        source = cast("Path", self.source)
        dest = cast("Path", self.dest)
        return calculate_diff(self.path, source, dest, color=color, max_lines=max_lines)


Changes = list[Change]


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
