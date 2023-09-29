from dataclasses import dataclass

from ... import backup
from ...utils import Path


@dataclass
class Backup(backup.Backup):
    dest: Path = Path.backup_cache

    def generate_path_rules(self):
        dest_pattern = Backup.dest.relative_to(self.original_source)
        yield f"- /{dest_pattern}/**"
        yield from super().generate_path_rules()
