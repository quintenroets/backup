import json

import pytest

from backup.backup import Backup
from backup.context.context import Context
from backup.models import Change, ChangeType, Path


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_status() -> None:
    backup = Backup()
    status = backup.capture_status(quiet=True)

    expected_changes = (
        Change(Path("0.txt"), ChangeType.modified),
        Change(Path("1.txt"), ChangeType.created),
        Change(Path("2.txt"), ChangeType.deleted),
    )
    for change in status:
        change.source = change.dest = None
    for change in expected_changes:
        assert change in status


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_push() -> None:
    backup = Backup()
    hash_value = backup.source.content_hash
    backup.capture_push()
    backup.push()
    assert not backup.capture_status().paths
    assert backup.source.content_hash == hash_value


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_pull() -> None:
    backup = Backup()
    hash_value = backup.dest.content_hash
    backup.capture_pull()
    backup.pull()
    assert not backup.capture_status().paths
    assert backup.dest.content_hash == hash_value


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_ls() -> None:
    backup = Backup()
    path = next(path for path in backup.source.iterdir() if path.is_file())
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_single_file_copy() -> None:
    backup = Backup()
    path = next(backup.source.iterdir())
    backup.capture_output("copyto", path, backup.dest / path.relative_to(backup.source))


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_all_options(test_context: Context) -> None:
    overwrite_newer = test_context.config.overwrite_newer
    test_context.config.overwrite_newer = False
    backup = Backup()
    backup.capture_push()
    test_context.config.overwrite_newer = overwrite_newer


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_show_diff(test_context: Context) -> None:
    backup = Backup()
    (backup.source / "0.txt").lines = ["same", "different"]
    (backup.dest / "0.txt").lines = ["same", "different2"]
    test_context.options.show_file_diffs = True
    changes = backup.capture_status()
    changes.ask_confirm(message="message", show_diff=True)
    changes.changes[0].print()
    test_context.options.show_file_diffs = False


@pytest.mark.usefixtures("mocked_backup")
def test_path_used() -> None:
    path = Path("dummy.txt")
    assert Backup(path=path).paths == (path,)


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_directory_used() -> None:
    directory = Path("dummy")
    assert Backup(directory=directory).paths == (directory / "**",)
