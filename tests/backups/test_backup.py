import json

from backup import Backup as MainBackup
from backup.backup import Backup
from backup.models import Change, ChangeType, Path


def test_status(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup(
        mocked_backup_with_filled_content.source, mocked_backup_with_filled_content.dest
    )
    status = backup.capture_status(quiet=True)

    expected_changes = (
        Change(Path("1.txt"), ChangeType.created),
        Change(Path("2.txt"), ChangeType.deleted),
        Change(Path("3.txt"), ChangeType.modified),
    )
    for change in status:
        change.source = change.dest = None
    for change in expected_changes:
        assert change in status


def test_push(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup(
        mocked_backup_with_filled_content.source, mocked_backup_with_filled_content.dest
    )
    backup.capture_push()
    backup.push()
    assert not backup.capture_status().paths


def test_pull(
    mocked_backup_with_filled_content: MainBackup,
) -> None:
    backup = Backup(
        mocked_backup_with_filled_content.source, mocked_backup_with_filled_content.dest
    )
    backup.capture_pull()
    backup.pull()
    assert not backup.capture_status().paths


def test_ls(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup(
        mocked_backup_with_filled_content.source, mocked_backup_with_filled_content.dest
    )
    path = next(backup.source.iterdir())
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


def test_single_file_copy(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup(
        mocked_backup_with_filled_content.source, mocked_backup_with_filled_content.dest
    )
    path = next(backup.source.iterdir())
    backup.capture_output("copyto", path, backup.dest / path.relative_to(backup.source))
