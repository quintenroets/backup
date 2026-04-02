from unittest.mock import MagicMock, patch

from backup.backup import Backup
from backup.backup.cache.checkers.detailed import RcloneChecker
from backup.backup.cache.checkers.path import extract_hash_path
from backup.backup.cache.entry import Entry
from backup.models import BackupConfig, Path


def test_detailed_checker(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    path = config.source / ".config" / "gtkrc"
    entry = Entry(config=config, source=path)
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
    entry = Entry(config=config, source=path)
    assert not entry.only_volatile_content_changed()
    hash_path = extract_hash_path(entry.dest, config)
    hash_path.text = RcloneChecker().calculate_content_hash()
    entry.dest.touch()
    path.text = " "
    assert entry.only_volatile_content_changed()
    mocked_run.assert_called()
    mocked_xattr.assert_called()
    assert len(list(entry.get_paths())) == 2


def test_hash_path_not_set_when_hashes_outside_source(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    with Path.tempdir() as source:
        sub_config = BackupConfig(source=source, dest=config.dest, cache=config.cache)
        path = source / "file.txt"
        path.touch()
        entry = Entry(config=sub_config, source=path)
        entry.only_volatile_content_changed()
        assert entry.hash_path is None
