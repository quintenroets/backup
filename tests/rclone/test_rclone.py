from unittest.mock import patch
from collections.abc import Iterator

import cli

from backup.rclone import Rclone, RcloneConfig
import json


from backup.context.context import Context
from backup.models import Change, ChangeTypes, Path

import pytest


@pytest.mark.parametrize("backup_class", [Rclone])
def test_setup_trigger(backup_class: type[Rclone]) -> None:
    with patch("backup.utils.setup.check_setup") as mocked_setup:
        backup_class()
        mocked_setup.assert_called_once()


def test_rclone_command() -> None:
    rclone = Rclone()
    rclone.run("version")


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_status() -> None:
    expected_changes = {
        Change(Path("0.txt"), ChangeTypes.modified),
        Change(Path("1.txt"), ChangeTypes.created),
        Change(Path("2.txt"), ChangeTypes.deleted),
    }
    assert capture_changes() == expected_changes


def capture_changes() -> set[Change]:
    backup = Rclone()
    status = backup.capture_status(quiet=True)
    return {Change(change.path, change.type) for change in status}


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_push() -> None:
    backup = Rclone()
    hash_value = backup.config.source.content_hash
    backup.capture_push()
    backup.push()
    assert not backup.capture_status().paths
    assert backup.config.source.content_hash == hash_value


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_pull() -> None:
    backup = Rclone()
    hash_value = backup.config.dest.content_hash
    backup.capture_pull()
    backup.pull()
    assert not backup.capture_status().paths
    assert backup.config.dest.content_hash == hash_value


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_ls() -> None:
    backup = Rclone()
    path = next(path for path in backup.config.source.iterdir() if path.is_file())
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_single_file_copy() -> None:
    backup = Rclone()
    path = next(backup.config.source.iterdir())
    backup.capture_output(
        "copyto", path, backup.config.dest / path.relative_to(backup.config.source)
    )


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_all_options(test_context: Context) -> None:
    overwrite_newer = test_context.config.overwrite_newer
    test_context.config.overwrite_newer = False
    backup = Rclone()
    backup.capture_push()
    test_context.config.overwrite_newer = overwrite_newer


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_show_diff(test_context: Context) -> None:
    backup = Rclone()
    (backup.config.source / "0.txt").lines = ["same", "different"]
    (backup.config.dest / "0.txt").lines = ["same", "different2"]
    test_context.options.show_file_diffs = True
    changes = backup.capture_status()
    changes.ask_confirm(message="message", show_diff=True)
    changes.changes[0].print()
    test_context.options.show_file_diffs = False


@pytest.fixture
def mocked_backup_with_root_dest(
    mocked_backup_with_filled_content: Rclone,  # noqa: ARG001
) -> Iterator[Rclone]:
    backup = Rclone()
    cli.run("rm -r", backup.config.dest)
    cli.run("sudo mkdir", backup.config.dest)
    yield backup
    cli.run("sudo rm -r", backup.config.dest)


def test_push_to_root_dest(mocked_backup_with_root_dest: Rclone) -> None:
    source_hash = mocked_backup_with_root_dest.config.source.content_hash
    mocked_backup_with_root_dest.push()
    assert not mocked_backup_with_root_dest.capture_status().paths
    assert mocked_backup_with_root_dest.config.source.content_hash == source_hash


def test_pull_to_root_source(mocked_backup_with_root_dest: Rclone) -> None:
    config = RcloneConfig(
        source=mocked_backup_with_root_dest.config.dest,
        dest=mocked_backup_with_root_dest.config.source,
    )
    rclone = Rclone(config)
    dest_hash = rclone.config.dest.content_hash
    rclone.pull()
    assert not mocked_backup_with_root_dest.capture_status().paths
    assert rclone.config.dest.content_hash == dest_hash


def test_pull_with_specified_paths(
    mocked_backup_with_filled_content: Rclone,
) -> None:
    paths = mocked_backup_with_filled_content.capture_status().paths
    config = RcloneConfig(
        source=mocked_backup_with_filled_content.config.dest,
        dest=mocked_backup_with_filled_content.config.source,
        paths=paths,
    )
    rclone = Rclone(config)
    dest_hash = rclone.config.dest.content_hash
    rclone.pull()
    assert not mocked_backup_with_filled_content.capture_status().paths
    assert rclone.config.dest.content_hash == dest_hash
