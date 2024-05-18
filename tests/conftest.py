from collections.abc import Iterator

import pytest
from backup.models import Path
from superpathlib.encryption import EncryptedPath


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
def folder(path: Path) -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture()
def folder2(path2: Path) -> Iterator[Path]:
    yield from provision_directory()


@pytest.fixture()
def encryption_path(path: Path) -> Iterator[EncryptedPath]:
    with path.encrypted as encryption_path:
        yield encryption_path
    assert not encryption_path.exists()
