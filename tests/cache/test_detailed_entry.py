from unittest.mock import MagicMock, patch

from backup.backup import Backup
from backup.backup.cache.checkers.detailed import RcloneChecker
from backup.backup.cache.checkers.path import extract_hash_path
from backup.backup.cache.detailed_entry import Entry


def detailed_checker(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    path = config.source / ".config" / "gtkrc"
    entry = Entry(source_root=config.source, dest_root=config.dest, source=path)
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
    mocked_backup: Backup,
) -> None:
    config = mocked_backup.backup_configs[0]
    path = config.source / ".config" / "rclone" / "rclone.conf"
    path.touch()
    entry = Entry(source_root=config.source, dest_root=config.dest, source=path)
    assert not entry.only_volatile_content_changed()
    hash_path = extract_hash_path(entry.dest)
    hash_path.text = RcloneChecker().calculate_content_hash()
    entry.dest.touch()
    path.text = " "
    assert entry.only_volatile_content_changed()
    mocked_run.assert_called()
    mocked_xattr.assert_called()
