from unittest.mock import MagicMock, patch

import pytest
from backup.backups.cache.checker.path import (
    KwalletChecker,
    PathChecker,
    RcloneChecker,
    UserPlaceChecker,
)
from backup.context import Context
from backup.models import Path


@pytest.fixture()
def checker(test_context: Context) -> PathChecker:  # noqa: ARG001
    return PathChecker()


def test_non_existing_file(checker: PathChecker) -> None:
    with Path.tempfile(create=False) as path:
        assert checker.calculate_relevant_hash(path) == hash(None)


def test_empty_file(checker: PathChecker) -> None:
    with Path.tempfile() as path:
        assert checker.calculate_relevant_hash(path) == hash(())


def test_sections(checker: PathChecker) -> None:
    with Path.tempfile() as path:
        path.lines = ["[header]", "content"]
        checker.calculate_relevant_hash(path)


@pytest.mark.usefixtures("test_context")
def test_user_place_checker() -> None:
    checker = UserPlaceChecker()
    with Path.tempfile() as path:
        path.text = '<bookmark href="https://www.example.com">'
        checker.calculate_relevant_hash(path)


@patch("cli.capture_output_lines", return_value=[""])
@pytest.mark.usefixtures("test_context")
def test_rclone_checker(mocked_run: MagicMock) -> None:
    checker = RcloneChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path)
    mocked_run.assert_called()


@patch("cli.capture_output_lines", return_value=[""])
@pytest.mark.usefixtures("test_context")
def test_kwallet_checker(mocked_run: MagicMock) -> None:
    checker = KwalletChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path)
    mocked_run.assert_called()
