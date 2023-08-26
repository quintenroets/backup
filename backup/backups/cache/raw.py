from dataclasses import dataclass

from ... import backup
from ...utils import Path


@dataclass
class Backup(backup.Backup):
    dest: Path = Path.backup_cache
