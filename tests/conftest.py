import sys
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any
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


@dataclass
class ContextList(AbstractContextManager[None]):
    items: list[AbstractContextManager[Any]]

    def __enter__(self) -> None:
        for item in self.items:
            item.__enter__()

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        for item in self.items:
            item.__exit__(exception_type, exception_value, traceback)


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


def generate_context_managers(
    directories: list[Path],
) -> Iterator[AbstractContextManager[Any]]:
    yield from directories
    root = directories[0]
    yield mock_under_test_root(root=root, path=Path.config)
    yield mock_under_test_root(root=root, path=Path.resume)


def mock_under_test_root(
    root: Path, path: Path, name: str | None = None
) -> AbstractContextManager[Any]:
    if name is None:
        name = path.name.lower()
    return_value = root / path.relative_to(Path.backup_source)
    mocked_path = PropertyMock(return_value=return_value)
    return patch.object(Path, name, new_callable=mocked_path)


@pytest.fixture()
def test_context(context: Context) -> Iterator[Context]:
    directories = [Path.tempdir() for _ in range(2)]
    restored_directories = (
        context.config.backup_source,
        context.config.backup_dest,
        context.config.cache_path,
    )
    context_managers = list(generate_context_managers(directories))
    relative_cache_path = Path.backup_cache.relative_to(Path.backup_source)
    with ContextList(context_managers):
        (context.config.backup_source, context.config.backup_dest) = directories
        context.config.cache_path = context.config.backup_source / relative_cache_path
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
    for number in (0, 1):
        fill(mocked_backup.source, content, number=number)
    content2 = content * 2
    for number in (0, 2):
        fill(mocked_backup.dest, content2, number=number)
    add_profile_paths(test_context.profiles_source_root)


def add_profile_paths(root: Path) -> None:
    name = Defaults.create_profile_paths()[0]
    path = root / name
    path.touch()


@pytest.fixture
def mocked_backup_with_filled_content_for_pull(
    mocked_backup_with_filled_content: Backup, test_context: Context
) -> Backup:
    profile_path = test_context.config.backup_dest / Path.HOME.relative_to(
        Path.backup_source
    )
    add_profile_paths(profile_path)
    return mocked_backup_with_filled_content


def fill(directory: Path, content: str = "content", number: int = 0) -> None:
    path = directory / f"{number}.txt"
    path.text = content
