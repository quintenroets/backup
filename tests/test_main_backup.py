import pytest
from backup import Backup
from backup.models import Action

from tests.test_backup import fill


def test_main_backup(mocked_backup: Backup) -> None:
    fill(mocked_backup.source, b"")
    fill(mocked_backup.source, b" ", number=1)
    mocked_backup.run_action(Action.push)
    fill(mocked_backup.source, b" ", number=2)
    mocked_backup.run_action(Action.push)
    mocked_backup.run_action(Action.pull)


def test_malformed_filters_indicated(mocked_backup: Backup) -> None:
    mocked_backup.filter_rules = ["?"]
    with pytest.raises(ValueError):
        mocked_backup.capture_status()
