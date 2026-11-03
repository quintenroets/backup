import pytest

from backup.models import BackupConfig, Ignores, Path, SyncRecord
from backup.scanners import scan_sources
from backup.syncer import FileState, PathRule


def scan(backup_config: BackupConfig) -> list[str]:
    return scan_sources([backup_config])[0].paths


def create_files(root: Path, *relatives: str) -> None:
    for relative in relatives:
        (root / relative).text = "content"


@pytest.mark.parametrize(
    ("includes", "ignores", "relatives", "expected"),
    [
        (("debug.log",), Ignores(patterns=["*.log"]), ("debug.log",), []),
        (
            ("cache/kept",),
            Ignores(names=["cache"]),
            ("cache/dropped.txt", "cache/kept/file.txt"),
            ["cache/kept/file.txt"],
        ),
        (
            (),
            Ignores(patterns=["build/cache"]),
            ("build/cache/file.txt", "build/keep.txt"),
            ["build/keep.txt"],
        ),
    ],
)
def test_ignores_prune_the_walk(
    backup_config: BackupConfig,
    includes: tuple[str, ...],
    ignores: Ignores,
    relatives: tuple[str, ...],
    expected: list[str],
) -> None:
    """An ignore beats a file include but not one below it, on the relative path."""
    backup_config.scope.rules.extend(PathRule.select(includes))
    backup_config.scope.ignores = ignores
    create_files(backup_config.source, *relatives)
    assert scan(backup_config) == expected


@pytest.mark.parametrize(("mtime_delta", "size_delta"), [(-1.0, 0), (0.0, 1)])
def test_modified(
    backup_config: BackupConfig,
    mtime_delta: float,
    size_delta: int,
) -> None:
    source_file = backup_config.source / "file.txt"
    source_file.text = "content"
    state = FileState(source_file.mtime + mtime_delta, source_file.size + size_delta)
    backup_config.records["file.txt"] = SyncRecord(state)
    assert scan(backup_config) == ["file.txt"]


@pytest.mark.parametrize(
    ("name", "expected"),
    [("file.txt", []), ("file.zip", ["file.zip"])],
)
def test_oversized_file_is_omitted_unless_zipped(
    backup_config: BackupConfig,
    name: str,
    expected: list[str],
) -> None:
    """An oversized file backed up earlier must not read as deleted."""
    backup_config.scope.max_backup_size = 1
    backup_config.records[name] = SyncRecord()
    create_files(backup_config.source, name)
    assert scan(backup_config) == expected


@pytest.mark.parametrize(
    ("includes", "mode"),
    [((), 0), (("locked",), 0), ((), 0o444)],
)
def test_unreadable_path_stops_the_scan(
    backup_config: BackupConfig,
    includes: tuple[str, ...],
    mode: int,
) -> None:
    """Read as deleted, its records would make the push delete their remote copies."""
    backup_config.scope.rules.extend(PathRule.select(includes))
    create_files(backup_config.source, "locked/file.txt")
    directory = backup_config.source / "locked"
    directory.chmod(mode)
    try:
        with pytest.raises(PermissionError):
            scan(backup_config)
    finally:
        directory.chmod(0o755)
