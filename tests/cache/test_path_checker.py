from unittest.mock import MagicMock, patch

import pytest
from backup.backups.cache.checker.path import (
    KwalletChecker,
    PathChecker,
    RcloneChecker,
    UserPlaceChecker,
)
from backup.models import Path


@pytest.fixture
def checker() -> PathChecker:
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


def test_user_place_checker() -> None:
    checker = UserPlaceChecker()
    with Path.tempfile() as path:
        path.text = '<bookmark href="https://www.example.com">'
        checker.calculate_relevant_hash(path)


def test_rclone_checker() -> None:
    checker = RcloneChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path)


@patch("cli.capture_output_lines", return_value=[""])
def test_kwallet_checker(_: MagicMock) -> None:
    checker = KwalletChecker()
    with Path.tempfile() as path:
        checker.calculate_relevant_hash(path)
