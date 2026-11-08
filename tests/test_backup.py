from collections.abc import Iterator
from unittest.mock import patch

import pytest

from backup.backup import Backup, run
from backup.backup.cache import CacheScanner
from backup.context import Action, context
from backup.models import Change, Path, PathRule, PrintStructure


@pytest.fixture
def backup() -> Iterator[Backup]:
    with Path.tempdir() as source, Path.tempdir() as dest, Path.tempdir() as cache:
        sync = {"includes": [""]}
        yield Backup({"source": source, "dest": dest, "cache": cache, "syncs": [sync]})


@pytest.mark.parametrize("action", Action)
def test_run(action: Action) -> None:
    with (
        patch.object(context.options, "action", action),
        patch.object(Backup, action.value, autospec=True) as method,
    ):
        run({})
    method.assert_called_once()


@pytest.mark.parametrize("deleted", [False, True])
def test_push_file(backup: Backup, *, deleted: bool) -> None:
    config = backup.backup_configs[0]
    path = Path("0.txt")
    ((config.cache if deleted else config.source) / path).touch()
    config.rules = [PathRule(path, include=True)]
    changes = backup.push()[0]
    assert len(changes) == 1
    assert changes[0].path == path
    assert not backup.push()[0]


def test_print_nested_changes() -> None:
    paths = ("a/b/0", "a/b/c/0", "a/b/c/1")
    PrintStructure.from_changes([Change(Path(path)) for path in paths]).print()


def test_scan_skips_nested_cache(backup: Backup) -> None:
    config = backup.backup_configs[0]
    path = Path("cache/0.txt")
    config.cache = config.source / path.parent
    (config.source / path).touch()
    entries = CacheScanner(config).generate_entries()
    assert path not in {entry.relative for entry in entries}


def test_pull(backup: Backup) -> None:
    config = backup.backup_configs[0]
    (config.source / "0.txt").touch(mtime=60)
    (config.dest / "0.txt").touch(mtime=60)
    (config.dest / "1.txt").touch()
    (config.cache / "2.txt").touch()
    assert len(backup.pull()[0]) == 1
    assert (config.source / "1.txt").exists()
