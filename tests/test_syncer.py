import os
from collections.abc import Callable, Iterator
from unittest.mock import patch

import cli
import pytest

from backup import create_syncer, resolve_remote
from backup.models import Path
from backup.syncer import (
    PathRule,
    RcloneConfig,
    Syncer,
    load_rclone_env,
    requires_root,
)
from tests.conftest import BackupSetup


@pytest.fixture
def syncer(backup: BackupSetup) -> Syncer:
    for number in (0, 1):
        (backup.source / f"{number}.txt").text = "content"
    for number in (0, 2):
        (backup.dest / f"{number}.txt").text = "content" * 2
    return Syncer(backup.source, backup.dest)


def test_list_remote_files(syncer: Syncer) -> None:
    files = syncer.list_remote_files()
    expected_file = syncer.dest / "0.txt"
    assert files["0.txt"].size == expected_file.size
    assert files["0.txt"].mtime == pytest.approx(expected_file.mtime)


def verify_push(syncer: Syncer) -> None:
    source_hash = syncer.source.content_hash
    syncer.capture_push()
    assert_no_differences(syncer)
    assert syncer.source.content_hash == source_hash


def verify_pull(syncer: Syncer) -> None:
    dest_hash = syncer.dest.content_hash
    syncer.capture_pull()
    assert_no_differences(syncer)
    assert syncer.dest.content_hash == dest_hash


def assert_no_differences(syncer: Syncer) -> None:
    syncer.transfer(cli.capture_output, "check")


@pytest.mark.parametrize("verify", [verify_push, verify_pull])
def test_sync(syncer: Syncer, verify: Callable[[Syncer], None]) -> None:
    verify(syncer)


@pytest.mark.parametrize("overwrite_newer", [False, True])
def test_update_option_preserves_newer_files(*, overwrite_newer: bool) -> None:
    """--update is what stops a push from overwriting a newer remote file."""
    options = RcloneConfig(overwrite_newer=overwrite_newer)
    generated = Syncer(Path("/"), Path("dest:"), rclone=options).generate_options()
    assert ("--update" in generated) != overwrite_newer


@pytest.fixture
def root_owned_syncer(syncer: Syncer) -> Iterator[Syncer]:
    dest = syncer.dest
    cli.run("rm -r", dest)
    cli.run("sudo mkdir", dest)
    yield syncer
    cli.run("sudo rm -r", dest)


def test_push_to_root_dest(root_owned_syncer: Syncer) -> None:
    verify_push(root_owned_syncer)


@pytest.mark.parametrize(("source", "folder"), [(Path.HOME, "home"), (Path("/"), "")])
def test_create_syncer_scopes_path_to_remote(source: Path, folder: str) -> None:
    syncer = create_syncer(source / "file.txt")
    assert syncer.source == source
    assert syncer.dest == Path(resolve_remote()) / folder
    assert syncer.rules == PathRule.select(["file.txt"])


def test_missing_dest_takes_write_access_from_its_nearest_ancestor() -> None:
    """A first backup creates the dest, which must not make it look root-owned."""
    with Path.tempdir() as directory:
        assert not requires_root(directory / "missing" / "dest")


def test_remote_dest_never_requires_root() -> None:
    with patch("os.access", return_value=False, autospec=True):
        assert not requires_root(Path("remote:backup"))


def test_export_files(syncer: Syncer) -> None:
    syncer.export_files("csv")
    remote_only_file = syncer.source / "2.txt"
    assert remote_only_file.text == (syncer.dest / "2.txt").text


def test_load_rclone_password() -> None:
    load_rclone_env.cache_clear()
    with (
        patch.dict(os.environ, {"RCLONE_PASSWORD_COMMAND": "command"}),
        patch("backup.syncer.load_secret", return_value="secret"),
    ):
        env = load_rclone_env()
    load_rclone_env.cache_clear()
    assert env["RCLONE_CONFIG_PASS"] == "secret"  # noqa: S105
    assert "RCLONE_PASSWORD_COMMAND" not in env
