import pytest
from backup.models import Path


def provision_path():
    with Path.tempfile() as path:
        yield path
    assert not path.exists()


def provision_directory():
    with Path.tempdir() as path:
        yield path
    assert not path.exists()


@pytest.fixture()
def path():
    yield from provision_path()


@pytest.fixture()
def path2():
    yield from provision_path()


@pytest.fixture()
def folder(path):
    yield from provision_directory()


@pytest.fixture()
def folder2(path2):
    yield from provision_directory()


@pytest.fixture()
def encryption_path(path):
    with path.encrypted as encryption_path:
        yield encryption_path
    assert not encryption_path.exists()
