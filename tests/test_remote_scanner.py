from backup.backup.models import BackupConfig, Ignores, Path, SyncRecord
from backup.backup.scanners.remote import generate_changes
from backup.syncer import FileState, PathRule


def changed_paths(backup_config: BackupConfig, *relatives: str) -> list[str]:
    remote_files = {name: FileState(1.0, 1) for name in relatives}
    changes = generate_changes(backup_config, remote_files)
    return [str(change.path) for change in changes]


def test_ignored_file_is_not_pulled(backup_config: BackupConfig) -> None:
    backup_config.scope.ignores = Ignores(patterns=["logs/*.log"])
    paths = changed_paths(backup_config, "logs/debug.log", "logs/keep.txt")
    assert paths == ["logs/keep.txt"]


def test_ignored_directory_name_covers_the_files_under_it(
    backup_config: BackupConfig,
) -> None:
    """A basename check misses these: the ignored component is a parent."""
    backup_config.scope.ignores = Ignores(names=["node_modules"])
    paths = changed_paths(
        backup_config,
        "project/node_modules/left-pad/index.js",
        "project/main.py",
    )
    assert paths == ["project/main.py"]


def test_ignored_record_generates_no_deletion(backup_config: BackupConfig) -> None:
    backup_config.scope.ignores = Ignores(patterns=["logs/*.log"])
    backup_config.sync_state.update("logs/debug.log", SyncRecord())
    assert changed_paths(backup_config) == []


def test_missing_record_generates_a_deletion(backup_config: BackupConfig) -> None:
    backup_config.sync_state.update("file.txt", SyncRecord())
    assert changed_paths(backup_config) == ["file.txt"]


def test_record_outside_the_rules_generates_no_deletion(
    backup_config: BackupConfig,
) -> None:
    """Narrowed rules leave a record out of scope, which is not the same as gone."""
    backup_config.scope.rules = [
        PathRule(Path("kept"), include=True),
        PathRule(Path(), include=False),
    ]
    backup_config.sync_state.update("dropped/file.txt", SyncRecord())
    assert changed_paths(backup_config) == []


def test_sub_check_keeps_patterns_anchored_at_the_sync_source(
    backup_config: BackupConfig,
) -> None:
    backup_config.scope.ignores = Ignores(patterns=["outer/logs/*.log"])
    backup_config.scope.sub_path = Path("outer")
    paths = changed_paths(backup_config, "logs/debug.log", "logs/keep.txt")
    assert paths == ["logs/keep.txt"]
