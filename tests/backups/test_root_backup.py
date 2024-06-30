from collections.abc import Iterator

import cli
import pytest
from backup.backup import Backup
from backup.backups import Backup as MainBackup
from backup.models import Path


@pytest.fixture()
def mocked_backup_with_root_dest(
    mocked_backup_with_filled_content: MainBackup,
) -> Iterator[Backup]:
    backup = Backup()
    cli.run("rm -r", backup.dest)
    cli.run("sudo mkdir", backup.dest)
    yield backup
    cli.run("sudo rm -r", backup.dest)


def test_push(mocked_backup_with_root_dest: Backup) -> None:
    source_hash = mocked_backup_with_root_dest.source.content_hash
    mocked_backup_with_root_dest.push()
    assert not mocked_backup_with_root_dest.capture_status().paths
    assert mocked_backup_with_root_dest.source.content_hash == source_hash


def test_pull(mocked_backup_with_root_dest: Backup) -> None:
    backup = Backup(
        source=mocked_backup_with_root_dest.dest,
        dest=mocked_backup_with_root_dest.source,
    )
    dest_hash = backup.dest.content_hash
    backup.push(reverse=True)
    assert not mocked_backup_with_root_dest.capture_status().paths
    assert backup.dest.content_hash == dest_hash


def test_extract_path(mocked_backup_with_root_dest: Backup) -> None:
    path = Path("0.txt")
    backup = Backup(path=path)
    paths = list(backup.extract_root_paths(reverse=False))
    assert paths == [path]


def test_extract_directory(mocked_backup_with_root_dest: Backup) -> None:
    backup = Backup(directory=Path(""))
    paths = list(backup.extract_root_paths(reverse=False))
    assert paths == [Path("**")]


def test_pull_with_specified_paths(
    mocked_backup_with_filled_content: MainBackup,
) -> None:
    paths = mocked_backup_with_filled_content.capture_status().paths
    backup = Backup(
        source=mocked_backup_with_filled_content.dest,
        dest=mocked_backup_with_filled_content.source,
        paths=paths,
    )
    dest_hash = backup.dest.content_hash
    backup.process_root_dest(reverse=True)
    assert not mocked_backup_with_filled_content.capture_status().paths
    assert backup.dest.content_hash == dest_hash
