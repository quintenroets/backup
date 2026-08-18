from backup.backup.models import BackupConfig, ChangeTypes, Ignores, Path, SyncRecord
from backup.backup.scanners.source import SourceScanner
from backup.syncer import PathRule


def scan(backup_config: BackupConfig) -> list[str]:
    changes = SourceScanner(backup_config).generate_changes()
    return [str(change.path) for change in changes if change is not None]


def test_nested_include_rule_scans_once(backup_config: BackupConfig) -> None:
    backup_config.scope.rules.append(PathRule(Path("sub"), include=True))
    (backup_config.source / "sub").mkdir()
    (backup_config.source / "sub" / "file.txt").text = "content"
    assert scan(backup_config) == ["sub/file.txt"]


def test_exclude_rule_overrides_included_root(backup_config: BackupConfig) -> None:
    backup_config.scope.rules.append(PathRule(Path("excluded.txt"), include=False))
    (backup_config.source / "excluded.txt").text = "content"
    (backup_config.source / "included.txt").text = "content"
    assert scan(backup_config) == ["included.txt"]


def test_exclude_rule_prunes_directory(backup_config: BackupConfig) -> None:
    backup_config.scope.rules.append(PathRule(Path("excluded"), include=False))
    (backup_config.source / "excluded").mkdir()
    (backup_config.source / "excluded" / "file.txt").text = "content"
    assert scan(backup_config) == []


def test_include_rule_overrides_excluded_directory(backup_config: BackupConfig) -> None:
    backup_config.scope.rules.append(PathRule(Path("excluded"), include=False))
    backup_config.scope.rules.append(PathRule(Path("excluded/kept"), include=True))
    (backup_config.source / "excluded" / "kept").mkdir(parents=True)
    (backup_config.source / "excluded" / "dropped.txt").text = "content"
    (backup_config.source / "excluded" / "kept" / "file.txt").text = "content"
    assert scan(backup_config) == ["excluded/kept/file.txt"]


def test_excluded_record_is_not_scanned(backup_config: BackupConfig) -> None:
    backup_config.scope.rules.append(PathRule(Path("excluded.txt"), include=False))
    backup_config.sync_state.update("excluded.txt", SyncRecord())
    assert scan(backup_config) == []


def test_ignored_file_rule_is_not_scanned(backup_config: BackupConfig) -> None:
    """An include naming a file loses to a global ignore, like one naming a folder."""
    backup_config.scope.rules.append(PathRule(Path("debug.log"), include=True))
    backup_config.scope.ignores = Ignores(patterns=["*.log"])
    (backup_config.source / "debug.log").text = "content"
    assert scan(backup_config) == []


def test_include_rule_under_ignored_directory_is_scanned(
    backup_config: BackupConfig,
) -> None:
    backup_config.scope.rules.append(PathRule(Path("cache/kept"), include=True))
    backup_config.scope.ignores = Ignores(names=["cache"])
    (backup_config.source / "cache" / "kept").mkdir(parents=True)
    (backup_config.source / "cache" / "dropped.txt").text = "content"
    (backup_config.source / "cache" / "kept" / "file.txt").text = "content"
    assert scan(backup_config) == ["cache/kept/file.txt"]


def test_newly_ignored_directory_covers_the_records_under_it(
    backup_config: BackupConfig,
) -> None:
    backup_config.scope.ignores = Ignores(names=["cache"])
    backup_config.sync_state.update("cache/data.bin", SyncRecord())
    (backup_config.source / "cache").mkdir(parents=True)
    (backup_config.source / "cache" / "data.bin").text = "content"
    changes = SourceScanner(backup_config).generate_changes()
    types = [change.type for change in changes if change is not None]
    assert types == [ChangeTypes.deleted]


def test_newly_ignored_record_is_deleted(backup_config: BackupConfig) -> None:
    """The remote holds what is actively backed up, not a permanent archive."""
    backup_config.scope.ignores = Ignores(patterns=["*.log"])
    backup_config.sync_state.update("debug.log", SyncRecord())
    (backup_config.source / "debug.log").text = "content"
    changes = SourceScanner(backup_config).generate_changes()
    types = [change.type for change in changes if change is not None]
    assert types == [ChangeTypes.deleted]


def test_deleted_record_is_scanned(backup_config: BackupConfig) -> None:
    backup_config.sync_state.update("deleted.txt", SyncRecord())
    assert scan(backup_config) == ["deleted.txt"]


def test_anchored_pattern_excludes_file(backup_config: BackupConfig) -> None:
    """Patterns are matched against the source-relative path."""
    backup_config.scope.ignores = Ignores(patterns=["logs/*.log"])
    (backup_config.source / "logs").mkdir()
    (backup_config.source / "logs" / "debug.log").text = "content"
    (backup_config.source / "logs" / "keep.txt").text = "content"
    assert scan(backup_config) == ["logs/keep.txt"]


def test_anchored_pattern_prunes_directory(backup_config: BackupConfig) -> None:
    backup_config.scope.ignores = Ignores(patterns=["build/cache"])
    (backup_config.source / "build" / "cache").mkdir(parents=True)
    (backup_config.source / "build" / "cache" / "file.txt").text = "content"
    (backup_config.source / "build" / "keep.txt").text = "content"
    assert scan(backup_config) == ["build/keep.txt"]


def test_suffix_pattern_excludes_partial_download(backup_config: BackupConfig) -> None:
    backup_config.scope.ignores = Ignores(patterns=["*.part"])
    (backup_config.source / "file.part").text = "content"
    (backup_config.source / "file.txt").text = "content"
    assert scan(backup_config) == ["file.txt"]


def test_sub_check_keeps_patterns_anchored_at_the_sync_source(
    backup_config: BackupConfig,
) -> None:
    """A sub-checked run re-roots the source, so the prefix is added back."""
    backup_config.scope.ignores = Ignores(patterns=["outer/logs/*.log"])
    backup_config.scope.sub_path = Path("outer")
    backup_config.source /= "outer"
    (backup_config.source / "logs").mkdir(parents=True)
    (backup_config.source / "logs" / "debug.log").text = "content"
    (backup_config.source / "logs" / "keep.txt").text = "content"
    assert scan(backup_config) == ["logs/keep.txt"]
