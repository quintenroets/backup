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
                is_file = source_path.is_file() or dest_path.is_file()
                if is_file:
                    if source_path.exists():
                        yield Entry(self.backup, source=source_path)
                    else:
                        yield Entry(self.backup, dest=dest_path)
                else:
                    for entry_path in source_path.find(exclude=self.exclude_root):
                        yield Entry(self.backup, source=entry_path)
                    for entry_path in dest_path.find(
                        exclude=lambda path_: path_ in self.visited,
                    ):
                        yield Entry(self.backup, dest=entry_path)
            self.visited.add(source_path)
            self.visited.add(dest_path)

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or self.backup.ignores.matches(path)
            or path.is_symlink()
        )
