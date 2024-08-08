from unittest.mock import patch

import pytest
from backup.backups import Backup
from backup.context.context import Context
from backup.models import Action, Path

from tests.mocks.storage import Defaults


def test_status(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.status)


def test_diff(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.run_action(Action.diff)


def test_show_diff(
    mocked_backup_with_filled_content: Backup,
    test_context: Context,
) -> None:
    test_context.options.show_file_diffs = True
    mocked_backup_with_filled_content.run_action(Action.push)
    test_context.options.show_file_diffs = False


def test_empty_push(mocked_backup: Backup) -> None:
    mocked_backup.run_action(Action.push)


def test_push(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content)


def test_push_with_indent(mocked_backup_with_filled_content: Backup) -> None:
    directory = mocked_backup_with_filled_content.source / "sub" / "directory"
    paths = (
        directory / "a.txt",
        directory / "b.txt",
        directory / "sub_sub" / "a.txt",
        directory / "sub_sub" / "b.txt",
    )
    for path in paths:
        path.touch()
    verify_push(mocked_backup_with_filled_content)


def test_push_with_profile(
    mocked_backup_with_filled_content: Backup,
    test_context: Context,
) -> None:
    path = test_context.profiles_path / Defaults.create_profile_paths()[0]
    path.touch()
    verify_push(mocked_backup_with_filled_content)


@pytest.mark.usefixtures("mocked_backup_with_filled_content")
def test_pull(test_context: Context) -> None:
    verify_pull(test_context)


def test_pull_with_sub_path(
    mocked_backup_with_filled_content: Backup,
    test_context: Context,
) -> None:
    verify_pull(test_context, backup=mocked_backup_with_filled_content)


def test_pull_with_profile(
    mocked_backup_with_filled_content: Backup,
    test_context: Context,
) -> None:
    profile_path = (
        test_context.config.backup_dest
        / test_context.profiles_path.relative_to(test_context.config.backup_source)
    )
    path = profile_path / Defaults.create_profile_paths()[0]
    path.touch()
    verify_pull(test_context, backup=mocked_backup_with_filled_content)


def test_malformed_filters_indicated(mocked_backup: Backup) -> None:
    mocked_backup.filter_rules = ["????"]
    with pytest.raises(ValueError, match="Invalid paths:"):
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


def verify_pull(context: Context, backup: Backup | None = None) -> None:
    if backup is None:
        backup = Backup()
    backup.run_action(Action.pull)
    dest_file = next(
        path for path in context.config.backup_dest.rglob("*") if path.is_file()
    )
    dest_file.unlink()
    backup.run_action(Action.pull)


def test_detailed_checker(test_context: Context) -> None:
    path = test_context.profiles_source_root / ".config" / "gtkrc"
    path.touch()
    with patch("xattr.xattr.set"):
        Backup().run_action(Action.push)
        path.text = "#"
        Backup().run_action(Action.push)


def test_detailed_checker_hash_path(test_context: Context) -> None:
    path = test_context.profiles_source_root / ".config" / "rclone" / "rclone.conf"
    path.touch()
    with patch("xattr.xattr.set"):
        Backup().run_action(Action.push)
        path.text = " "
        Backup().run_action(Action.push)


@pytest.mark.usefixtures("test_context")
def test_after_pull(mocked_backup: Backup) -> None:
    Path.selected_resume_pdf.touch()
    path = Path.selected_resume_pdf.relative_to(mocked_backup.source)
    mocked_backup.paths = [path]
    mocked_backup.after_pull()


@pytest.mark.usefixtures(
    "mocked_backup_with_filled_content",
    "test_context_with_sub_check_path",
)
def test_profile_parent_sub_check_path() -> None:
    backup = Backup()
    backup.dest.mkdir(parents=True)
    verify_push(backup)
