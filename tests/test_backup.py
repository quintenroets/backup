from unittest.mock import patch

import pytest

from backup.backup import Backup, run
from backup.context import Action, context
from backup.models import BackupConfig, Path, PathRule


def test_push(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content)


def test_empty_push(mocked_backup: Backup) -> None:
    mocked_backup.push()


@pytest.mark.parametrize("action", Action)
def test_run(action: Action, mocked_backup: Backup) -> None:
    with (
        patch.object(context.options, "action", action),
        patch.object(Backup, action.value) as method,
    ):
        run(mocked_backup.config)
    method.assert_called_once()


def test_push_with_reversed_cache(mocked_backup_with_filled_content: Backup) -> None:
    verify_push(mocked_backup_with_filled_content, reverse_cache=True)


def verify_push(backup: Backup, *, reverse_cache: bool = False) -> None:
    if reverse_cache:
        config = backup.backup_configs[0]
        config.source, config.cache = config.cache, config.source
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
