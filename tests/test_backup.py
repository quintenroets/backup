from unittest.mock import patch

import pytest

from backup.backup import Backup
from backup.models import BackupConfig, Path, PathRule


def test_status(mocked_backup_with_filled_content: Backup) -> None:
    mocked_backup_with_filled_content.status()


def test_empty_push(mocked_backup: Backup) -> None:
    mocked_backup.push()


@pytest.fixture
def mocked_backup_with_include_path(
    mocked_backup_with_filled_content: Backup,
) -> Backup:
    mocked_backup_with_filled_content.backup_configs[0].rules.append(
        PathRule(Path("0.txt"), include=True),
    )
    return mocked_backup_with_filled_content


def test_push(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content)


def test_push_with_include_path(mocked_backup_with_include_path: Backup) -> None:
    verify_push(mocked_backup_with_include_path)


def test_push_with_reversed_cache(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content, reverse_cache=True)


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


def verify_push(backup: Backup, *, reverse_cache: bool = False) -> None:
    if reverse_cache:
        config = backup.backup_configs[0]
        config.source, config.cache = config.cache, config.source
    backup.push()
    backup.push()


def verify_pull(test_backup_config: BackupConfig, backup: Backup) -> None:
    backup.pull()
    dest_file = next(
        path for path in test_backup_config.dest.rglob("*") if path.is_file()
    )
    dest_file.unlink()
    backup.pull()


def test_detailed_checker(mocked_backup: Backup) -> None:
    path = mocked_backup.backup_configs[0].source / ".config" / "gtkrc"
    path.touch()
    with patch("xattr.xattr.set"):
        mocked_backup.push()
        path.text = "#"
        mocked_backup.push()


def test_detailed_checker_hash_path(mocked_backup: Backup) -> None:
    path = mocked_backup.backup_configs[0].source / ".config" / "syncer" / "syncer.conf"
    path.touch()
    with patch("xattr.xattr.set"):
        mocked_backup.push()
        path.text = " "
        mocked_backup.push()


def test_after_pull(mocked_backup: Backup) -> None:
    Path.selected_resume_pdf.touch()
    path = Path.selected_resume_pdf.relative_to(mocked_backup.backup_configs[0].source)
    rule = PathRule(path, include=True)
    mocked_backup.backup_configs[0].rules.append(rule)
    mocked_backup.pull()
    mocked_backup.backup_configs[0].rules.pop(-1)
