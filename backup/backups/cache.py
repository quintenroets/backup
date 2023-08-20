from dataclasses import dataclass

import cli

from .. import backup
from ..utils import Path
from . import cache_to_remote


@dataclass
class Backup(backup.Backup):
    quiet: bool = True
    dest: Path = Path.backup_cache

    def __post_init__(self):
        if not self.dest.exists():
            self.create_dest()
        super().__post_init__()

    def create_dest(self):
        commands = (f"mkdir {self.dest}", f"chown -R $(whoami):$(whoami) {self.dest}")
        cli.sh(*commands, root=True)
        cache_to_remote.Backup().pull()
