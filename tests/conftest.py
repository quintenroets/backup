import os
import sys
from collections.abc import Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass
from types import TracebackType
from typing import Any, cast
from unittest.mock import PropertyMock, patch

import cli
import pytest
import superpathlib
from package_utils.storage import CachedFileContent

from backup.backup import Backup
from backup.context import context as context_
from backup.context.context import Context
from backup.models import BackupConfig, Path
from backup.storage import Storage
from backup.syncer import SyncConfig, Syncer
from backup.utils.setup import check_setup
from tests import mocks
from tests.mocks.methods import mocked_method


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


def provision_directory() -> Iterator[Path]:
    with Path.tempdir() as path:
        yield path
    assert not path.exists()


@pytest.fixture
def directory() -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture(scope="session", autouse=True)
def _setup_syncer() -> None:
    check_setup()


@pytest.fixture(scope="session", autouse=True)
def test_context() -> Context:
    os.environ["USERNAME"] = (
        "runner" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
    )
    return context_


def generate_context_managers(
    directories: list[Path],
) -> Iterator[AbstractContextManager[Any]]:
    yield from directories
    root = directories[0]
    yield mock_under_test_root(root=root, path=Path.resume)
    yield mock_under_test_root(root=root, path=Path.hashes)
    yield patch("cli.track_progress", new=lambda *args, **_: args[0])


def mock_under_test_root(
    root: Path,
    path: Path,
    name: str | None = None,
) -> AbstractContextManager[Any]:
    if name is None:
        name = path.name.lower()
    return_value = root / path.relative_to(Path.backup_source)
    mocked_path = PropertyMock(return_value=return_value)
    return patch.object(Path, name, new_callable=mocked_path)


@pytest.fixture
def mocked_backup() -> Iterator[Backup]:
    directories = [Path.tempdir() for _ in range(2)]
    context_managers = list(generate_context_managers(directories))
    relative_cache_path = Path.backup_cache.relative_to(Path.backup_source)
    item = {"includes": [""], "excludes": ["dummy.txt", "dummy_directory"]}
    config = {
        "source": str(directories[0]),
        "dest": str(directories[1]),
        "cache": str(directories[0] / relative_cache_path),
        "syncs": [item],
    }
    with ContextList(context_managers):
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
def mocked_storage(test_context: Context) -> Iterator[None]:
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
    patched_storage = patch.object(test_context, "storage", new_callable=mock_storage)
    patches = [patched_storage, *patched_cli_methods, *patched_methods]
    with ContextList(cast("list[AbstractContextManager[Any]]", patches)):
        yield None


@pytest.fixture
def mocked_syncer(test_backup_config: BackupConfig) -> Syncer:
    config = SyncConfig(
        source=test_backup_config.source,
        dest=test_backup_config.dest,
        sub_check_path=test_backup_config.source,
    )
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
