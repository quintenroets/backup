import os
import subprocess
from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest

from backup.context import context
from backup.models import ChangeType
from backup.path import Path
from backup.syncer import SyncConfig, Syncer
from backup.syncer.builder import create_syncer
from backup.syncer.cli_runner import load_rclone_env


@pytest.fixture
def syncer() -> Iterator[Syncer]:
    with Path.tempdir() as source, Path.tempdir() as dest:
        yield Syncer(SyncConfig(source=source, dest=dest))


@pytest.fixture
def filled_syncer(syncer: Syncer) -> Syncer:
    for number in (0, 1):
        (syncer.config.source / f"{number}.txt").text = "a"
    for number in (0, 2):
        (syncer.config.dest / f"{number}.txt").text = "aa"
    (syncer.config.dest / "directory" / "file.txt").text = "aa"
    return syncer


def test_rclone_failures_raise(syncer: Syncer) -> None:
    syncer.config.dest = Path("missing:")
    with pytest.raises(subprocess.CalledProcessError):
        syncer.capture_status()


def test_status(filled_syncer: Syncer) -> None:
    for directory in (filled_syncer.config.source, filled_syncer.config.dest):
        (directory / "3.txt").text = "a"
    status = filled_syncer.capture_status()
    changes = {change.path: change.type for change in status}
    assert changes == {
        Path("0.txt"): ChangeType.modified,
        Path("1.txt"): ChangeType.created,
        Path("2.txt"): ChangeType.deleted,
        Path("directory") / "file.txt": ChangeType.deleted,
    }


def test_push(filled_syncer: Syncer) -> None:
    source_hash = filled_syncer.config.source.content_hash
    filled_syncer.capture_push()
    assert filled_syncer.config.dest.content_hash == source_hash


def test_pull(filled_syncer: Syncer) -> None:
    dest_hash = filled_syncer.config.dest.content_hash
    filled_syncer.capture_pull()
    assert filled_syncer.config.source.content_hash == dest_hash


def test_push_skips_newer(syncer: Syncer) -> None:
    (syncer.config.source / "0.txt").touch(mtime=1)
    dest = syncer.config.dest / "0.txt"
    dest.text = "newer"
    with patch.object(context.config.rclone, "update", new=True):
        syncer.capture_push()
    assert dest.text == "newer"


@pytest.fixture
def syncer_with_root_dest(filled_syncer: Syncer) -> Iterator[Syncer]:
    config = filled_syncer.config
    cli.run("rm -r", config.dest)
    cli.run("sudo mkdir", config.dest)
    yield filled_syncer
    cli.run("sudo rm -r", config.dest)


def test_push_to_root_dest(syncer_with_root_dest: Syncer) -> None:
    source_hash = syncer_with_root_dest.config.source.content_hash
    syncer_with_root_dest.push()
    assert syncer_with_root_dest.config.dest.content_hash == source_hash


def test_pull_with_specified_paths(filled_syncer: Syncer) -> None:
    config = filled_syncer.config
    Syncer(config.with_paths([Path("2.txt"), Path("directory")])).capture_pull()
    assert (config.source / "2.txt").exists()
    assert (config.source / "directory").exists()
    assert (config.source / "1.txt").exists()


def test_create_syncer() -> None:
    create_syncer(Path.HOME)


def test_export_files(syncer: Syncer) -> None:
    syncer.export_files("csv")


def test_load_rclone_password() -> None:
    with (
        patch.dict(os.environ, {"RCLONE_PASSWORD_COMMAND": "command"}),
        patch("backup.syncer.cli_runner.load_secret", return_value="secret"),
    ):
        env = load_rclone_env.__wrapped__()
    assert env["RCLONE_CONFIG_PASS"] == "secret"  # noqa: S105
    assert "RCLONE_PASSWORD_COMMAND" not in env
