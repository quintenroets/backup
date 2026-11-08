from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from superpathlib import Path


class ChangeType(StrEnum):
    created = "+"
    modified = "*"
    deleted = "-"
    preserved = "="


@dataclass(unsafe_hash=True)
class Change:
    path: Path
    type: ChangeType = ChangeType.created
    source: Path | None = None
    dest: Path | None = None


Changes = list[Change]
