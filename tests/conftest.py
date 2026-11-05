import os
import sys
from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest
import superpathlib

from backup.backup import Backup
from backup.context import Context, Storage
from backup.context import context as context_
from backup.models import BackupConfig, Path
from backup.syncer import SyncConfig, Syncer


@pytest.fixture(scope="session", autouse=True)
def _rclone_test_config() -> Iterator[None]:
    os.environ.pop("RCLONE_PASSWORD_COMMAND", None)
    with Path.tempfile() as config_path, Path.tempdir() as remote_directory:
        config = {
            "RCLONE_CONFIG": str(config_path),
            "RCLONE_CONFIG_BACKUPMASTER_TYPE": "alias",
            "RCLONE_CONFIG_BACKUPMASTER_REMOTE": str(remote_directory),
        }
        os.environ.update(config)
        yield


@pytest.fixture(scope="session", autouse=True)
def test_context() -> Context:
    os.environ["USERNAME"] = (
        "runner" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
    )
    return context_


@pytest.fixture
def mocked_backup() -> Iterator[Backup]:
    with Path.tempdir() as source, Path.tempdir() as dest:
        config = {
            "source": str(source),
            "dest": str(dest),
            "cache": str(source / Path.backup_cache.relative_to(Path.backup_source)),
            "syncs": [{"includes": [""], "excludes": ["dummy.txt", "dummy_directory"]}],
        }
        yield Backup(config)


@pytest.fixture
def mocked_backup_with_filled_content(
    mocked_syncer_with_filled_content: Syncer,  # noqa: ARG001
    mocked_backup: Backup,
) -> Backup:
    return mocked_backup


@pytest.fixture
def test_backup_config(mocked_backup: Backup) -> BackupConfig:
    return mocked_backup.backup_configs[0]


@pytest.fixture(scope="session", autouse=True)
def isolated_session() -> Iterator[None]:
    with (
        patch.object(Storage, "number_of_paths", 0),
        patch.object(cli, "confirm", return_value=True),
        patch.object(sys.stdin, "isatty", return_value=True),
    ):
        yield


@pytest.fixture
def mocked_syncer(test_backup_config: BackupConfig) -> Syncer:
    config = SyncConfig(source=test_backup_config.source, dest=test_backup_config.dest)
    return Syncer(config)


@pytest.fixture
def mocked_syncer_with_filled_content(mocked_syncer: Syncer) -> Syncer:
    fill_directories(mocked_syncer)
    return mocked_syncer


def fill_directories(mocked_syncer: Syncer, content: str = "content") -> None:
    for number in (0, 1):
        fill(mocked_syncer.config.source, content, number=number)
    content2 = content * 2
    for number in (0, 2):
        fill(mocked_syncer.config.dest, content2, number=number)


def fill(
    directory: superpathlib.Path,
    content: str = "content",
    number: int = 0,
) -> None:
    path = directory / f"{number}.txt"
    path.text = content
