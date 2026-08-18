from __future__ import annotations

import typing
from dataclasses import dataclass, field
from enum import StrEnum

from .path import Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover

    from backup.syncer import FileState  # pragma: nocover


class Action(StrEnum):
    """The direction of a transfer, and so the side of a record it observes."""

    push = "push"
    pull = "pull"


@dataclass(frozen=True, order=True)
class ChangeType:
    sort_order: int
    color: str
    symbol: str


class ChangeTypes:
    created = ChangeType(0, "green", "+")
    modified = ChangeType(1, "blue", "*")
    deleted = ChangeType(2, "red", "-")


@dataclass
class Change:
    path: Path
    type: ChangeType
    local_state: FileState | None = None
    remote_state: FileState | None = None
    conflict: bool = False

    @property
    def sort_index(self) -> tuple[ChangeType, Path]:
        return self.type, self.path


@dataclass
class Changes:
    """The changes one sync found, addressed relative to the root it covers."""

    changes: list[Change] = field(default_factory=list)
    source: Path = field(default_factory=Path)

    def __post_init__(self) -> None:
        self.changes = sorted(self.changes, key=lambda change: change.sort_index)

    def __iter__(self) -> Iterator[Change]:
        yield from self.changes

    def __bool__(self) -> bool:
        return bool(self.changes)

    def __len__(self) -> int:
        return len(self.changes)

    @property
    def paths(self) -> list[Path]:
        return [change.path for change in self.changes]

    @property
    def absolute_paths(self) -> list[Path]:
        return [self.source / change.path for change in self.changes]
