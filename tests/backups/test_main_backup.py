from unittest.mock import MagicMock, patch

import pytest
from backup import Backup
from backup.context.context import Context
from backup.models import Action, Path


def test_status(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.status)


def test_diff(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.diff)


def test_show_diff(
    mocked_backup_with_filled_content: Backup, test_context: Context
) -> None:
    test_context.options.show_file_diffs = True
    mocked_backup_with_filled_content.run_action(Action.push)
    test_context.options.show_file_diffs = False


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


@patch("xattr.xattr.set")
def test_detailed_checker(
    _: MagicMock, mocked_backup_with_filled_content: Backup, test_context: Context
) -> None:
    path_to_check = test_context.profiles_source_root / ".config" / "gtkrc"
    path_to_check.touch()
    mocked_backup_with_filled_content.run_action(Action.push)
    path_to_check.text = "#"
    Backup().run_action(Action.push)


def test_after_pull(mocked_backup: Backup, test_context: Context) -> None:
    path = Path.resume.relative_to(mocked_backup.source)
    mocked_backup.paths = [path]
    mocked_backup.after_pull()
