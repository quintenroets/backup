from unittest.mock import PropertyMock, patch

import pytest

from backup.backup import Backup
from backup.models import BackupConfig, Path, PathRule
from backup.syncer import Syncer


def test_status(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.status()


def test_push(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content)


def test_empty_push(mocked_backup: Backup) -> None:
    mocked_backup.push()


def test_push_with_reversed_cache(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content, reverse_cache=True)


def verify_push(backup: Backup, *, reverse_cache: bool = False) -> None:
    if reverse_cache:
        config = backup.backup_configs[0]
        hash_path = config.cache / Path.hashes.relative_to(config.source)
        config.source, config.cache = config.cache, config.source

    else:
        hash_path = Path.hashes
    mocked_path = PropertyMock(return_value=hash_path)
    with patch.object(Path, "hashes", new_callable=mocked_path):
        backup.push()
        backup.push()


@pytest.fixture
def mocked_backup_with_include_path(
    mocked_backup_with_filled_content: Backup,
) -> Backup:
    mocked_backup_with_filled_content.backup_configs[0].rules.append(
        PathRule(Path("0.txt"), include=True),
    )
    return mocked_backup_with_filled_content


def test_push_with_include_path(mocked_backup_with_include_path: Backup) -> None:
    verify_push(mocked_backup_with_include_path)


def test_push_with_reversed_cache_and_include_path(
    mocked_backup_with_include_path: Backup,
) -> None:
    verify_push(mocked_backup_with_include_path, reverse_cache=True)


def test_push_with_indent(mocked_backup_with_filled_content: Backup) -> None:
    directory = (
        mocked_backup_with_filled_content.backup_configs[0].source / "sub" / "directory"
    )
    paths = (
        directory / "a.txt",
        directory / "b.txt",
        directory / "sub_sub" / "a.txt",
        directory / "sub_sub" / "b.txt",
    )
    for path in paths:
        path.touch()
    verify_push(mocked_backup_with_filled_content)


def test_pull(
    mocked_backup_with_filled_content: Backup,
    test_backup_config: BackupConfig,
) -> None:
    verify_pull(test_backup_config, backup=mocked_backup_with_filled_content)


def test_pull_with_sub_path(
    mocked_backup_with_filled_content: Backup,
    test_backup_config: BackupConfig,
) -> None:
    verify_pull(test_backup_config, backup=mocked_backup_with_filled_content)


def verify_pull(test_backup_config: BackupConfig, backup: Backup) -> None:
    backup.pull()
    dest_file = next(
        path for path in test_backup_config.dest.rglob("*") if path.is_file()
    )
    dest_file.unlink()
    backup.pull()


def test_after_pull(mocked_backup: Backup) -> None:
    Path.selected_resume_pdf.touch()
    config = mocked_backup.backup_configs[0]
    path = Path.selected_resume_pdf.relative_to(config.source)
    config.rules.append(PathRule(path, include=True))

    with (
        patch("backup.utils.exporter.export_resume") as patched_export,
        patch.object(Syncer, "capture_push", autospec=True) as patched_push,
    ):
        mocked_backup.pull()
    patched_export.assert_called_once()
    patched_push.assert_called_once()


def test_push_with_detailed_checker(mocked_backup: Backup) -> None:
    path = mocked_backup.backup_configs[0].source / ".config" / "gtkrc"
    path.touch()
    with patch("xattr.xattr.set"):
        mocked_backup.push()
        path.text = "#"
        mocked_backup.push()


def test_push_with_detailed_checker_hash_path(mocked_backup: Backup) -> None:
    path = mocked_backup.backup_configs[0].source / ".config" / "rclone" / "rclone.conf"
    path.touch()
    with patch("xattr.xattr.set"):
        mocked_backup.push()
        path.text = " "
        mocked_backup.push()
