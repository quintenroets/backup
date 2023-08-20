from dataclasses import dataclass

from ..utils import Path
from . import remote


@dataclass
class Backup(remote.Backup):
    quiet: bool = False
    source: Path = Path.backup_cache
