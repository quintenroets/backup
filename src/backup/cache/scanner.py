from collections.abc import Iterator
from dataclasses import dataclass, field

from superpathlib import Path

from backup.models import Backup

from .entry import Entry


@dataclass
class CacheScanner:
    backup: Backup
    visited: set[Path] = field(default_factory=set)

    def generate_entries(self) -> Iterator[Entry]:
        for rule in self.backup.rules:
            source_path = self.backup.source / rule.path
            dest_path = self.backup.cache / rule.path
            if rule.include:
                sources = source_path.find(Path.is_file, exclude=self.exclude_root)
                yield from (Entry(self.backup, source=path) for path in sources)
                cached = dest_path.find(Path.is_file, exclude=self.visited.__contains__)
                yield from (Entry(self.backup, dest=path) for path in cached)
            self.visited.add(source_path)
            self.visited.add(dest_path)

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or self.backup.ignores.matches(path)
            or path.is_symlink()
        )
