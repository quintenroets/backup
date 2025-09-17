from unittest.mock import MagicMock, patch

from backup.backup.cache.checkers.detailed import RcloneChecker
from backup.backup.cache.checkers.path import extract_hash_path
from backup.backup.cache.detailed_entry import Entry
from backup.context import Context
from backup.backup import Backup


def test_detailed_checker(test_context: Context, mocked_backup: Backup) -> None:
    path = mocked_backup.backup_configs.backups[0].source / ".config" / "gtkrc"
    entry = Entry(
        source_root=test_context.config.backup_source,
        dest_root=test_context.config.backup_dest,
        source=path,
    )
    path.touch()
    assert not entry.only_volatile_content_changed()
    path.text = "#"
    entry.dest.touch()
    assert entry.only_volatile_content_changed()


@patch("cli.capture_output_lines", return_value=[""])
@patch("xattr.xattr.set")
def test_detailed_checker_hash_path(
    mocked_xattr: MagicMock,
    mocked_run: MagicMock,
    test_context: Context,
    mocked_backup: Backup,
) -> None:
    path = (
        mocked_backup.backup_configs.backups[0].source
        / ".config"
        / "rclone"
        / "rclone.conf"
    )
    path.touch()
    entry = Entry(
        source_root=test_context.config.backup_source,
        dest_root=test_context.config.cache_path,
        source=path,
    )
    assert not entry.only_volatile_content_changed()
    hash_path = extract_hash_path(entry.dest)
    hash_path.text = RcloneChecker().calculate_content_hash()
    entry.dest.touch()
    path.text = " "
    assert entry.only_volatile_content_changed()
    mocked_run.assert_called()
    mocked_xattr.assert_called()
