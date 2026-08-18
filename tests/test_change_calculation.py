import pytest

from backup.backup.models import (
    BackupConfig,
    Change,
    ChangeType,
    ChangeTypes,
    Path,
    SyncRecord,
)
from backup.backup.scanners.source import SourceScanner
from backup.syncer import FileState


def scan(backup_config: BackupConfig, name: str = "file.txt") -> Change | None:
    scanner = SourceScanner(backup_config)
    return scanner.calculate_change(name, scanner.observe(name))


def calculate_change_type(
    backup_config: BackupConfig,
    name: str = "file.txt",
) -> ChangeType | None:
    change = scan(backup_config, name)
    return change.type if change is not None else None


def record_matching(path: Path) -> SyncRecord:
    return SyncRecord(FileState(path.mtime, path.size))


def test_created(backup_config: BackupConfig) -> None:
    source_file = backup_config.source / "file.txt"
    source_file.text = "content"
    change = scan(backup_config)
    assert change is not None
    assert change.type == ChangeTypes.created
    assert change.local_state == FileState(source_file.mtime, source_file.size)


def test_unchanged(backup_config: BackupConfig) -> None:
    source_file = backup_config.source / "file.txt"
    source_file.text = "content"
    backup_config.sync_state.update("file.txt", record_matching(source_file))
    assert calculate_change_type(backup_config) is None


@pytest.mark.parametrize(("mtime_delta", "size_delta"), [(-1.0, 0), (0.0, 1)])
def test_modified(
    backup_config: BackupConfig,
    mtime_delta: float,
    size_delta: int,
) -> None:
    source_file = backup_config.source / "file.txt"
    source_file.text = "content"
    state = FileState(source_file.mtime + mtime_delta, source_file.size + size_delta)
    backup_config.sync_state.update("file.txt", SyncRecord(state))
    assert calculate_change_type(backup_config) == ChangeTypes.modified


def test_deletion_carries_no_state(backup_config: BackupConfig) -> None:
    backup_config.sync_state.update("file.txt", SyncRecord())
    change = scan(backup_config)
    assert change is not None
    assert change.type == ChangeTypes.deleted
    assert change.local_state is None


def test_missing(backup_config: BackupConfig) -> None:
    assert calculate_change_type(backup_config) is None


def test_oversized_excluded(backup_config: BackupConfig) -> None:
    backup_config.scope.max_backup_size = 1
    (backup_config.source / "file.txt").text = "content"
    assert calculate_change_type(backup_config) is None


def test_oversized_zip_included(backup_config: BackupConfig) -> None:
    backup_config.scope.max_backup_size = 1
    (backup_config.source / "file.zip").text = "content"
    assert calculate_change_type(backup_config, "file.zip") == ChangeTypes.created
