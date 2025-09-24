from unittest.mock import MagicMock, patch

import pytest

from backup.backup.cache.checkers.path import (
    KwalletChecker,
    PathChecker,
    RcloneChecker,
    UserPlaceChecker,
)
from backup.models import BackupConfig, Path


@pytest.fixture
def checker() -> PathChecker:
    return PathChecker()


def test_non_existing_file(
    checker: PathChecker,
    test_backup_config: BackupConfig,
) -> None:
    with Path.tempfile(create=False) as path:
        assert checker.calculate_relevant_hash(path, test_backup_config) == hash(None)


def test_empty_file(checker: PathChecker, test_backup_config: BackupConfig) -> None:
    with Path.tempfile() as path:
        assert checker.calculate_relevant_hash(path, test_backup_config) == hash(())


def test_sections(checker: PathChecker, test_backup_config: BackupConfig) -> None:
    with Path.tempfile() as path:
        path.lines = ["[header]", "content"]
        checker.calculate_relevant_hash(path, test_backup_config)


def test_user_place_checker(test_backup_config: BackupConfig) -> None:
    checker = UserPlaceChecker()
    with Path.tempfile() as path:
        path.text = '<bookmark href="https://www.example.com">'
        checker.calculate_relevant_hash(path, test_backup_config)


@patch("cli.capture_output_lines", return_value=[""])
@pytest.mark.usefixtures("test_context")
def test_rclone_checker(
    mocked_run: MagicMock,
    test_backup_config: BackupConfig,
) -> None:
    checker = RcloneChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path, test_backup_config)
    mocked_run.assert_called()


@patch("cli.capture_output_lines", return_value=[""])
@pytest.mark.usefixtures("test_context")
def test_kwallet_checker(
    mocked_run: MagicMock,
    test_backup_config: BackupConfig,
) -> None:
    checker = KwalletChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path, test_backup_config)
    mocked_run.assert_called()
