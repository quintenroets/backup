from dataclasses import dataclass

from ... import backup
from ...utils import Path


@dataclass
class Backup(backup.Backup):
    dest: Path = Path.backup_cache

    def generate_path_rules(self):
        if Backup.dest.is_relative_to(self.original_source):
            dest_pattern = Backup.dest.relative_to(self.original_source)
            yield f"- /{dest_pattern}/**"
        if not self.paths:
            yield "+ *"
        yield from super().generate_path_rules()
