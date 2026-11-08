from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest

from backup import run
from backup.cache import CacheScanner
from backup.context import Action, context
from backup.models import Path, SerializedBackupConfig
from backup.parser import parse_config


@pytest.fixture
def config() -> Iterator[SerializedBackupConfig]:
    with Path.tempdir() as source, Path.tempdir() as dest, Path.tempdir() as cache:
        sync = {"includes": [""]}
        raw = {"source": source, "dest": dest, "cache": cache, "syncs": [sync]}
        yield SerializedBackupConfig.from_dict(raw)


@pytest.mark.parametrize("deleted", [False, True])
def test_push_file(config: SerializedBackupConfig, *, deleted: bool) -> None:
    path = Path("0.txt")
    ((config.cache if deleted else config.source) / path).touch()
    config.syncs[0].includes = [str(path)]
    assert run(config.dict()) == [config.source / path]
    assert not run(config.dict())


def test_declined_push(config: SerializedBackupConfig) -> None:
    (config.source / "long.txt").lines = [str(number) for number in range(20)]
    (config.source / "binary.bin").byte_content = b"\0"
    for number in range(1001):
        (config.source / "many" / f"{number}.txt").touch()
    with patch.object(cli, "confirm", return_value=False):
        assert not run(config.dict())
    assert not (config.dest / "long.txt").exists()


def test_scan_skips_nested_cache(config: SerializedBackupConfig) -> None:
    backup_config = next(parse_config(config.dict(), Path("/")))
    path = Path("cache/0.txt")
    backup_config.cache = backup_config.source / path.parent
    (backup_config.source / path).touch()
    entries = CacheScanner(backup_config).generate_entries()
    assert path not in {entry.relative for entry in entries}


def test_pull(config: SerializedBackupConfig) -> None:
    (config.source / "0.txt").touch(mtime=60)
    (config.dest / "0.txt").touch(mtime=60)
    (config.dest / "1.txt").text = "pulled"
    (config.cache / "2.txt").touch()
    with (
        patch.object(context.options, "action", Action.pull),
        patch.object(cli, "confirm", side_effect=[False, True]),
        cli.console.capture() as capture,
    ):
        assert run(config.dict()) == [config.source / "1.txt"]
    assert (config.source / "1.txt").exists()
    assert "@@ -0,0 +1 @@" in capture.get()
