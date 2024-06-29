from collections.abc import Iterator

import cli
import pytest
from backup.backups import Backup
from backup.models import Path


@pytest.fixture()
def mocked_backup_with_root_dest(
    mocked_backup_with_filled_content: Backup,
) -> Iterator[Backup]:
    cli.run("rm -r", mocked_backup_with_filled_content.dest)
    cli.run("sudo mkdir", mocked_backup_with_filled_content.dest)
    yield mocked_backup_with_filled_content
    cli.run("sudo rm -r", mocked_backup_with_filled_content.dest)


def test_push(mocked_backup_with_root_dest: Backup) -> None:
    mocked_backup_with_root_dest.run_push()
    assert not mocked_backup_with_root_dest.capture_status().paths


def test_extract_path(mocked_backup_with_root_dest: Backup) -> None:
    path = Path("0.txt")
    backup = Backup(path=path)
    paths = list(backup.extract_root_paths(reverse=False))
    assert paths == [path]


def test_extract_directory(mocked_backup_with_root_dest: Backup) -> None:
    backup = Backup(directory=Path(""))
    paths = list(backup.extract_root_paths(reverse=False))
    assert paths == [Path("**")]
