import sys
from collections.abc import Iterator
from unittest.mock import PropertyMock, patch

import cli
import pytest
from backup.backups.backup import Backup
from backup.context import context as context_
from backup.context.context import Context
from backup.models import Path
from backup.utils.setup import check_setup
from package_utils.storage import CachedFileContent

from tests import mocks
from tests.mocks.methods import mocked_method
from tests.mocks.storage import Storage


def provision_path() -> Iterator[Path]:
    with Path.tempfile() as path:
        yield path
    assert not path.exists()


def provision_directory() -> Iterator[Path]:
    with Path.tempdir() as path:
        yield path
    assert not path.exists()


@pytest.fixture()
def path() -> Iterator[Path]:
    yield from provision_path()


@pytest.fixture()
def directory(path: Path) -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture(scope="session", autouse=True)
def setup_rclone() -> None:
    check_setup()


@pytest.fixture(scope="session", autouse=True)
def context() -> Iterator[Context]:
    yield context_


@pytest.fixture()
def test_context(context: Context) -> Iterator[Context]:
    directories = [Path.tempdir() for _ in range(4)]
    restored_directories = (
        context.config.backup_source,
        context.config.backup_dest,
        context.config.cache_path,
        context.config.profiles_source_root,
    )
    with directories[0], directories[1], directories[2], directories[3]:
        (
            context.config.backup_source,
            context.config.backup_dest,
            context.config.cache_path,
            context.config.profiles_source_root,
        ) = directories
        yield context
        (
            context.config.backup_source,
            context.config.backup_dest,
            context.config.cache_path,
            context.config.profiles_source_root,
        ) = restored_directories


@pytest.fixture(scope="session", autouse=True)
def mocked_storage(context: Context) -> Iterator[None]:
    storage = Storage()
    mock_storage = PropertyMock(return_value=storage)
    patched_methods = [
        mocked_method(CachedFileContent, "__get__", mocks.CachedFileContent.__get__),
        mocked_method(CachedFileContent, "__set__", mocks.CachedFileContent.__set__),
    ]
    patched_cli_methods = [
        patch.object(cli, "confirm", return_value=True),
        patch.object(cli.console, "clear"),
        patch.object(sys.stdin, "isatty", return_value=True),
    ]
    patched_storage = patch.object(context, "storage", new_callable=mock_storage)
    patches = [patched_storage, *patched_cli_methods, *patched_methods]
    with patches[0], patches[1], patches[2], patches[3], patches[4], patches[5]:  # type: ignore[attr-defined]
        yield None


@pytest.fixture
def mocked_backup(test_context: Context) -> Backup:
    backup = Backup()
    backup.sub_check_path = backup.source
    return backup


@pytest.fixture
def mocked_backup_with_filled_content(mocked_backup: Backup) -> Backup:
    fill_directories(mocked_backup)
    return mocked_backup


def fill_directories(mocked_backup: Backup) -> None:
    content = b"content"
    content2 = content * 2
    fill(mocked_backup.source, content)
    fill(mocked_backup.source, content, number=1)
    fill(mocked_backup.source, content, number=3)

    fill(mocked_backup.dest, content)
    fill(mocked_backup.dest, content2, number=2)
    fill(mocked_backup.dest, content2, number=3)


def fill(directory: Path, content: bytes, number: int = 0) -> None:
    path = directory / f"{number}.txt"
    path.byte_content = content
