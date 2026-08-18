from __future__ import annotations

import os
import typing
from dataclasses import dataclass
from stat import S_ISREG

if typing.TYPE_CHECKING:
    from superpathlib import Path  # pragma: nocover


@dataclass
class PathRule:
    path: Path
    include: bool

    @property
    def depth(self) -> int:
        return len(self.path.parts)


def resolve_rules(rules: list[PathRule]) -> list[PathRule]:
    ordered = sorted(rules, key=lambda rule: (-rule.depth, not rule.include))
    decisions: dict[Path, PathRule] = {}
    for rule in ordered:
        decisions.setdefault(rule.path, rule)
    return list(decisions.values())


@dataclass(frozen=True)
class FileState:
    mtime: float = 0.0
    size: int = 0

    @classmethod
    def from_stat(cls, stat: os.stat_result) -> FileState:
        return cls(stat.st_mtime, stat.st_size)

    @classmethod
    def read(cls, path: Path) -> FileState:
        return cls.from_stat(path.stat())

    @classmethod
    def observe(cls, path: str) -> FileState | None:
        """The state of the regular file at a path, or nothing to back up there."""
        try:
            stat = os.stat(path)  # noqa: PTH116
        except OSError:
            stat = None
        return (
            cls.from_stat(stat) if stat is not None and S_ISREG(stat.st_mode) else None
        )
