from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from superpathlib import Path

from .models import PathRule


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    rules: list[PathRule] = field(default_factory=list)
    paths: Sequence[Path] = field(default_factory=list)
    path: Path | None = None
    directory: Path | None = None
    filter_rules: list[str] = field(default_factory=list)

    def with_paths(self, paths: Iterable[Path]) -> "SyncConfig":
        return SyncConfig(source=self.source, dest=self.dest, paths=list(paths))
