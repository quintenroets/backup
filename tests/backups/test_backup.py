import json

from backup.backup import Backup
from backup.backups import Backup as MainBackup
from backup.context.context import Context
from backup.models import Change, ChangeType, Path


def test_status(mocked_backup_with_filled_content: MainBackup) -> None:
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


def test_push(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup()
    backup.capture_push()
    backup.push()
    assert not backup.capture_status().paths


def test_pull(
    mocked_backup_with_filled_content: MainBackup,
) -> None:
    backup = Backup()
    backup.capture_pull()
    backup.pull()
    assert not backup.capture_status().paths


def test_ls(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup()
    path = next(path for path in backup.source.iterdir() if path.is_file())
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


def test_single_file_copy(mocked_backup_with_filled_content: MainBackup) -> None:
    backup = Backup()
    path = next(backup.source.iterdir())
    backup.capture_output("copyto", path, backup.dest / path.relative_to(backup.source))


def test_all_options(
    test_context: Context, mocked_backup_with_filled_content: MainBackup
) -> None:
    overwrite_newer = test_context.config.overwrite_newer
    test_context.config.overwrite_newer = False
    backup = Backup()
    backup.capture_push()
    test_context.config.overwrite_newer = overwrite_newer


def test_show_diff(
    mocked_backup_with_filled_content: Backup, test_context: Context
) -> None:
    backup = Backup()
    (backup.source / "0.txt").lines = ["same", "different"]
    (backup.dest / "0.txt").lines = ["same", "different2"]
    test_context.options.show_file_diffs = True
    changes = backup.capture_status()
    changes.ask_confirm(message="message", show_diff=True)
    changes.changes[0].print()
    test_context.options.show_file_diffs = False


def test_path_used(mocked_backup: Backup) -> None:
    path = Path("dummy.txt")
    assert Backup(path=path).paths == (path,)


def test_directory_used(mocked_backup_with_filled_content: Backup) -> None:
    directory = Path("dummy")
    assert Backup(directory=directory).paths == (directory / "**",)
