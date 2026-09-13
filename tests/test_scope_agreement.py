import pytest

from backup.backup.models import BackupConfig, Ignores, Path, Scope
from backup.backup.scanners.source import SourceScanner
from backup.syncer import PathRule

files = (
    "a.txt",
    "a/b.txt",
    "a/b/c.txt",
    "a/b/c/d.txt",
    "a/keep/z.txt",
    "ab/f.txt",
    "x.txt",
    "dir [a]/f.txt",
)

rule_sets = (
    (("", True),),
    (("a", True),),
    (("", True), ("a", False)),
    (("", True), ("a", False), ("a/b", True)),
    (("a", True), ("a/b", False), ("a/b/c", True)),
    (("", False), ("a/keep", True)),
    (("a", True), ("a", False)),
    (("", True), ("a/b/c/d.txt", False)),
    (("dir [a]", True),),
    (("", True), ("ab", False)),
)


@pytest.fixture
def scoped_backup_config(backup_config: BackupConfig) -> BackupConfig:
    """A config whose remote is its own source, so both sides see one tree."""
    for relative in files:
        path = backup_config.source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.text = "content"
    backup_config.dest = backup_config.source
    return backup_config


def walk(config: BackupConfig) -> set[str]:
    changes = SourceScanner(config).generate_changes()
    return {str(change.path) for change in changes if change is not None}


def list_remote(config: BackupConfig) -> set[str]:
    return set(config.create_syncer().list_remote_files())


def cover_records(config: BackupConfig) -> set[str]:
    return {relative for relative in files if config.scope.includes(relative)}


@pytest.mark.parametrize("rules", rule_sets)
def test_rules_select_the_same_paths_everywhere(
    scoped_backup_config: BackupConfig,
    rules: tuple[tuple[str, bool], ...],
) -> None:
    """One rule set read three ways: the walk, the record check and rclone."""
    config = scoped_backup_config
    config.scope = Scope(
        [PathRule(Path(path), include=include) for path, include in rules],
    )
    selected = list_remote(config)
    assert walk(config) == selected
    assert cover_records(config) == selected


def test_ignores_keep_the_listing_wider_than_the_walk(
    scoped_backup_config: BackupConfig,
) -> None:
    """Ignores stay in process, so the listing covers what the walk prunes."""
    config = scoped_backup_config
    config.scope = Scope([PathRule(Path(), include=True)], Ignores(names=["a"]))
    walked = walk(config)
    assert walked < list_remote(config)
    assert list_remote(config) - walked == {
        file for file in files if file.startswith("a/")
    }
