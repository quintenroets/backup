from unittest.mock import MagicMock, patch

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
    assert entry.is_changed()


@patch("cli.capture_output_lines", return_value=[""])
@patch("xattr.xattr.set")
def test_detailed_checker_hash_path(
    _: MagicMock, __: MagicMock, test_context: Context
) -> None:
    path = test_context.profiles_source_root / ".config" / "rclone" / "rclone.conf"
    path.touch()
    entry = Entry(
        source_root=test_context.config.backup_source,
        dest_root=test_context.config.backup_dest,
        source=path,
    )
    assert entry.is_changed()
