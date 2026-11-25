import os
from collections.abc import Iterator
from dataclasses import replace
from unittest.mock import patch

import cli
import pytest
from superpathlib import Path

from backup.models import RcloneConfig
from backup.syncer import Syncer, create_syncer, load_rclone_env


@pytest.fixture
def syncer() -> Iterator[Syncer]:
    with Path.tempdir() as source, Path.tempdir() as dest:
        yield Syncer(source, dest)


@pytest.fixture
def filled_syncer(syncer: Syncer) -> Syncer:
    for number in (0, 1):
        (syncer.source / f"{number}.txt").text = "a"
    for number in (0, 2):
        (syncer.dest / f"{number}.txt").text = "aa"
    (syncer.dest / "directory" / "file.txt").text = "aa"
    return syncer


def test_push_skips_newer(syncer: Syncer) -> None:
    (syncer.source / "0.txt").touch(mtime=1)
    dest = syncer.dest / "0.txt"
    dest.text = "newer"
    replace(syncer, config=RcloneConfig(update=True)).sync()
    assert dest.text == "newer"


@pytest.fixture
def syncer_with_root_dest(filled_syncer: Syncer) -> Iterator[Syncer]:
    cli.run("sudo chown -R root", filled_syncer.dest)
    yield filled_syncer
    cli.run("sudo rm -r", filled_syncer.dest)


def test_push_to_root_dest(syncer_with_root_dest: Syncer) -> None:
    source_hash = syncer_with_root_dest.source.content_hash
    syncer_with_root_dest.sync()
    assert syncer_with_root_dest.dest.content_hash == source_hash


def test_pull_with_specified_paths(filled_syncer: Syncer) -> None:
    filled_syncer.with_paths([Path("2.txt"), Path("directory")]).reversed.sync()
    assert (filled_syncer.source / "2.txt").exists()
    assert (filled_syncer.source / "directory").exists()
    assert (filled_syncer.source / "1.txt").exists()


def test_create_syncer() -> None:
    create_syncer(Path.HOME)


def test_export_files(syncer: Syncer) -> None:
    syncer.export_files("csv")


def test_load_rclone_password() -> None:
    with (
        patch.dict(os.environ, {"RCLONE_PASSWORD_COMMAND": "command"}),
        patch("backup.syncer.load_secret", return_value="secret"),
    ):
        env = load_rclone_env.__wrapped__()
    assert env["RCLONE_CONFIG_PASS"] == "secret"  # noqa: S105
    assert "RCLONE_PASSWORD_COMMAND" not in env
