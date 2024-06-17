from unittest.mock import MagicMock, patch

from backup.backups.cache.checker.detailed import RcloneChecker
from backup.backups.cache.checker.path import extract_hash_path
from backup.backups.cache.detailed_entry import Entry
from backup.context import Context


@patch("cli.capture_output_lines", return_value=[""])
@patch("xattr.xattr.set")
def test_detailed_checker(_: MagicMock, __: MagicMock, test_context: Context) -> None:
    path = test_context.profiles_source_root / ".config" / "gtkrc"
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
    _: MagicMock, __: MagicMock, test_context: Context
) -> None:
    path = test_context.profiles_source_root / ".config" / "rclone" / "rclone.conf"
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
