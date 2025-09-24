from backup.models import Path

from .sync_config import SyncConfig


class SyncConfigs:
    home = SyncConfig(source=Path.HOME, dest=Path.remote / "home")
    cache = SyncConfig(source=Path.backup_source, dest=Path.backup_cache)


def extract_sync_config(path: Path) -> SyncConfig:
    return SyncConfigs.home if path.is_relative_to(Path.HOME) else SyncConfig()
