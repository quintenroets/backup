from superpathlib import Path

from backup.path import Path as BackupPath

from .cli_runner import resolve_remote
from .sync_config import SyncConfig
from .syncer import Syncer


def create_syncer(path: Path) -> Syncer:
    source = BackupPath.backup_source
    dest = BackupPath(resolve_remote())
    if path.is_relative_to(BackupPath.HOME):
        source = BackupPath.HOME
        dest /= "home"
    return Syncer(SyncConfig(source=source, dest=dest, paths=[path]))
