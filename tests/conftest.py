from collections.abc import Iterator

import pytest
from backup.backups.backup import Backup
from backup.context import context as context_
from backup.context.context import Context
from backup.models import Path
from backup.utils.setup import check_setup


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
    yield Backup(source=directory, dest=directory2)


@pytest.fixture(autouse=True, scope="session")
def setup_rclone() -> None:
    check_setup()


@pytest.fixture(scope="session")
def context() -> Context:
    return context_


@pytest.fixture(scope="session", autouse=True)
def test_context(context: Context) -> Context:
    context.config.overwrite_newer = True
    return context
