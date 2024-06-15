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
from tests.mocks.storage import Defaults, Storage


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
    directories = [Path.tempdir() for _ in range(3)]
    restored_directories = (
        context.config.backup_source,
        context.config.backup_dest,
        context.config.cache_path,
    )
    with directories[0], directories[1], directories[2]:
        (
            context.config.backup_source,
            context.config.backup_dest,
            context.config.cache_path,
        ) = directories
        context.profiles_source_root.mkdir(parents=True)
        yield context
        (
            context.config.backup_source,
            context.config.backup_dest,
            context.config.cache_path,
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
def mocked_backup_with_filled_content(
    mocked_backup: Backup, test_context: Context
) -> Backup:
    fill_directories(mocked_backup, test_context)
    return mocked_backup


def fill_directories(
    mocked_backup: Backup, test_context: Context, content: str = "content"
) -> None:
    for number in (0, 1, 3):
        fill(mocked_backup.source, content, number=number)
    content2 = content * 2
    for number in (0, 2, 3):
        fill(mocked_backup.dest, content2, number=number)
    for name in Defaults.create_profile_paths():
        path = test_context.profiles_source_root / name
        path.touch()


def fill(directory: Path, content: str = "content", number: int = 0) -> None:
    path = directory / f"{number}.txt"
    path.text = content
