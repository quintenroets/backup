import pytest
from backup import Backup
from backup.context.context import Context
from backup.models import Action, Path


def test_status(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.status)


def test_diff(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.diff)


def test_empty_push(mocked_backup: Backup) -> None:
    mocked_backup.run_action(Action.push)


def test_push(mocked_backup_with_filled_content: Backup, test_context: Context) -> None:
    verify_push(mocked_backup_with_filled_content)


def test_pull(mocked_backup_with_filled_content: Backup) -> None:
    verify_pull(mocked_backup_with_filled_content)


def test_malformed_filters_indicated(mocked_backup: Backup) -> None:
    mocked_backup.filter_rules = ["????"]
    with pytest.raises(ValueError):
        mocked_backup.capture_status()


def test_sub_check_path(mocked_backup: Backup) -> None:
    sub_check_path = Path("subdirectory")
    mocked_backup = Backup(
        source=mocked_backup.source,
        dest=mocked_backup.dest,
        sub_check_path=sub_check_path,
    )
    verify_push(mocked_backup)


def verify_push(backup: Backup) -> None:
    backup.run_action(Action.push)
    backup.run_action(Action.push)


def verify_pull(backup: Backup) -> None:
    backup.run_action(Action.pull)
    dest_file = next(backup.dest.iterdir())
    dest_file.unlink()
    backup.run_action(Action.pull)
