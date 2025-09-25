from superpathlib import Path

from backup.models import Path as BackupPath

from .sync_config import SyncConfig


class SyncConfigs:
    home = SyncConfig(source=BackupPath.HOME, dest=BackupPath.remote / "home")
    cache = SyncConfig(source=BackupPath.backup_source, dest=BackupPath.backup_cache)


def select_sync_config(path: Path) -> SyncConfig:
    return SyncConfigs.home if path.is_relative_to(Path.HOME) else SyncConfig()
