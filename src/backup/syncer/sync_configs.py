from superpathlib import Path

from backup.models import Path as BackupPath

from .sync_config import SyncConfig


def create_sync_config(
    *,
    path: Path | None = None,
    directory: Path | None = None,
) -> SyncConfig:
    target = directory if directory is not None else path
    assert target is not None  # noqa: S101
    is_home = target.is_relative_to(BackupPath.HOME)
    source = BackupPath.HOME if is_home else BackupPath.backup_source
    dest = BackupPath.remote / "home" if is_home else BackupPath.remote
    return SyncConfig(source=source, dest=dest, path=path, directory=directory)
