from collections.abc import Iterable
from dataclasses import dataclass, field

from cli.commands.commands import CommandItem
from superpathlib import Path


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    options: list[CommandItem] = field(default_factory=list)
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] | tuple[Path] | set[Path] = field(default_factory=list)
    path: Path | None = None
    directory: Path | None = None

    def with_paths(self, paths: Iterable[Path]) -> "SyncConfig":
        return SyncConfig(
            source=self.source,
            dest=self.dest,
            options=self.options,
            paths=list(paths),
        )
