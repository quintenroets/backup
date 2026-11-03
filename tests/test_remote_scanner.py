from backup.models import BackupConfig, Ignores, Path, SyncRecord
from backup.scanners import detect_pull_changes
from backup.syncer import FileState, PathRule


def changed_paths(backup_config: BackupConfig, *relatives: str) -> list[str]:
    remote_files = {name: FileState(1.0, 1) for name in relatives}
    changes = detect_pull_changes(backup_config, remote_files)
    return [change.path for change in changes]


def test_ignores_apply_below_the_deepest_rule(backup_config: BackupConfig) -> None:
    """Push walks from the include root, so pull must not apply ignores above it."""
    backup_config.scope.rules.append(PathRule(Path("cache/kept"), include=True))
    backup_config.scope.ignores = Ignores(names=["cache"])
    backup_config.records["cache/deleted.txt"] = SyncRecord()
    relatives = ("cache/dropped.txt", "cache/kept/file.txt")
    assert changed_paths(backup_config, *relatives) == ["cache/kept/file.txt"]


def test_record_outside_the_rules_generates_no_deletion(
    backup_config: BackupConfig,
) -> None:
    """Narrowed rules leave a record out of scope, which is not the same as gone."""
    backup_config.scope.rules = [
        PathRule(Path("kept"), include=True),
        PathRule(Path(), include=False),
    ]
    backup_config.records["dropped/file.txt"] = SyncRecord()
    assert changed_paths(backup_config) == []
