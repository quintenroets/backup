from collections.abc import Iterator

import cli
import pytest
from backup import Backup

from tests.conftest import fill


@pytest.fixture()
def mocked_backup_with_root_dest(mocked_backup: Backup) -> Iterator[Backup]:
    mocked_backup.dest.rmdir()
    cli.run("sudo mkdir", mocked_backup.dest)
    yield mocked_backup
    cli.run("sudo rm -r", mocked_backup.dest)


def test_push(mocked_backup_with_root_dest: Backup) -> None:
    fill(mocked_backup_with_root_dest.source)
    mocked_backup_with_root_dest.run_push()
    assert not mocked_backup_with_root_dest.capture_status().paths
