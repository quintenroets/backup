from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from .backup_config import BackupConfig

if TYPE_CHECKING:
    from superpathlib import Path


@dataclass(frozen=True)
class Change:
    path: Path
    type: ChangeType


Changes = list[Change]
Plan = tuple[BackupConfig, Changes]


class ChangeType(StrEnum):
    created = "+"
    modified = "*"
    deleted = "-"
    preserved = "="
