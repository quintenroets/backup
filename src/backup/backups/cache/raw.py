from collections.abc import Iterator
from dataclasses import dataclass

from ... import backup
from ...models import Path


@dataclass
class Backup(backup.Backup):
    dest: Path = Path.backup_cache

    def generate_path_rules(self) -> Iterator[str]:
        if self.dest.is_relative_to(self.source):
            dest_pattern = self.dest.relative_to(self.source)
            yield f"- /{dest_pattern}/**"
        if not self.paths:
            yield "+ *"
        yield from super().generate_path_rules()
