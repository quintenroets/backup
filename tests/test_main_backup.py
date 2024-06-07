import pytest
from backup import Backup
from backup.models import Action, Path

from tests.test_backup import fill


def test_push(mocked_backup: Backup) -> None:
    verify_push(mocked_backup)


def test_pull(mocked_backup: Backup) -> None:
    fill(mocked_backup.source, b"")
    mocked_backup.run_action(Action.pull)


def test_malformed_filters_indicated(mocked_backup: Backup) -> None:
    mocked_backup.filter_rules = ["?"]
    with pytest.raises(ValueError):
        mocked_backup.capture_status()


def test_sub_check_path(mocked_backup: Backup) -> None:
    sub_check_path = Path("subdirectory")
    mocked_backup = Backup(
        source=mocked_backup.source,
        dest=mocked_backup.dest,
        sub_check_path=sub_check_path,
    )
    verify_push(mocked_backup)


def verify_push(mocked_backup: Backup) -> None:
    fill(mocked_backup.source, b"")
    fill(mocked_backup.source, b" ", number=1)
    mocked_backup.run_action(Action.push)
    fill(mocked_backup.source, b" ", number=2)
    mocked_backup.run_action(Action.push)
