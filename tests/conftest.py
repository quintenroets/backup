from collections.abc import Iterator
from unittest.mock import PropertyMock, patch

import pytest
from backup.backup import rclone
from backup.backups import profile
from backup.backups.backup import Backup
from backup.backups.cache import cache
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
def path2() -> Iterator[Path]:
    yield from provision_path()


@pytest.fixture()
def directory(path: Path) -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture()
def directory2(path2: Path) -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture()
def mocked_backup(directory: Path, directory2: Path) -> Iterator[Backup]:
    rclone.Rclone.source = directory
    rclone.Rclone.dest = directory2
    cache.Backup.source = directory
    yield Backup(source=directory, dest=directory2)


@pytest.fixture(scope="session", autouse=True)
def setup_rclone() -> None:
    check_setup()


@pytest.fixture(scope="session", autouse=True)
def context() -> Iterator[Context]:
    with Path.tempdir() as directory:
        profile.Backup.dest = directory
        yield context_


@pytest.fixture()
def test_context(context: Context) -> Iterator[Context]:
    context.config.overwrite_newer = False
    yield context
    context.config.overwrite_newer = True


@pytest.fixture()
def test_cli_open_context(context: Context) -> Iterator[Context]:
    context.options.configure = True
    yield context
    context.options.configure = False


@pytest.fixture(scope="session", autouse=True)
def mocked_storage(context: Context) -> Iterator[None]:
    storage = Storage()
    mock_storage = PropertyMock(return_value=storage)
    patched_methods = [
        mocked_method(CachedFileContent, "__get__", mocks.CachedFileContent.__get__),
        mocked_method(CachedFileContent, "__set__", mocks.CachedFileContent.__set__),
    ]
    patched_storage = patch.object(context, "storage", new_callable=mock_storage)
    patches = [patched_storage, *patched_methods]
    with patches[0], patches[1], patches[2]:  # type: ignore[attr-defined]
        yield None
