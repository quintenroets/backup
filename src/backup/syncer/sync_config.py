from collections.abc import Iterable
from dataclasses import dataclass, field

from superpathlib import Path


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)

    def with_paths(self, paths: Iterable[Path]) -> "SyncConfig":
        return SyncConfig(source=self.source, dest=self.dest, paths=list(paths))
