import pytest

from backup.models import BackupConfig, Ignores, Path, Scope
from backup.scanners import scan_sources
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
    (("a", True),),
    (("", True), ("a", False), ("a/b", True)),
    (("", False), ("a/keep", True)),
    (("a", True), ("a", False)),
    (("", True), ("a/b/c/d.txt", False)),
    (("dir [a]", True),),
    (("x.txt", True),),
)


@pytest.fixture
def config(backup_config: BackupConfig) -> BackupConfig:
    """A config whose remote is its own source, so both sides see one tree."""
    for relative in files:
        (backup_config.source / relative).text = "content"
    backup_config.dest = backup_config.source
    return backup_config


def walk(config: BackupConfig) -> set[str]:
    return set(scan_sources([config])[0].paths)


@pytest.mark.parametrize("rules", rule_sets)
def test_rules_select_the_same_paths_everywhere(
    config: BackupConfig,
    rules: tuple[tuple[str, bool], ...],
) -> None:
    """One rule set read three ways: the walk, the record check and rclone."""
    config.scope = Scope([PathRule(Path(path), include) for path, include in rules])
    selected = set(config.list_remote())
    assert walk(config) == selected
    assert {file for file in files if config.scope.includes(file)} == selected


def test_ignores_keep_the_listing_wider_than_the_walk(config: BackupConfig) -> None:
    """Ignores stay in process, so the listing covers what the walk prunes."""
    config.scope.ignores = Ignores(names=["a"])
    walked = walk(config)
    listed = set(config.list_remote())
    assert walked < listed
    assert listed - walked == {file for file in files if file.startswith("a/")}
