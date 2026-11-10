from superpathlib import Path

from backup.path import Path as BackupPath

from .cli_runner import resolve_remote
from .sync_config import SyncConfig
from .syncer import Syncer


def create_syncer(
    *,
    path: Path | None = None,
    directory: Path | None = None,
) -> Syncer:
    target = directory if directory is not None else path
    assert target is not None  # noqa: S101
    is_home = target.is_relative_to(BackupPath.HOME)
    source = BackupPath.HOME if is_home else BackupPath.backup_source
    remote = BackupPath(resolve_remote())
    dest = remote / "home" if is_home else remote
    return Syncer(SyncConfig(source=source, dest=dest, path=path, directory=directory))
