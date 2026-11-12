from collections.abc import Iterable
from dataclasses import dataclass, field, replace
from typing import Self

from superpathlib import Path

from backup.models import PathRule


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    rules: list[PathRule] = field(default_factory=list)

    def with_paths(self, paths: Iterable[Path]) -> Self:
        includes = [PathRule(path, include=True) for path in paths]
        return replace(self, rules=[*includes, PathRule(Path(), include=False)])
