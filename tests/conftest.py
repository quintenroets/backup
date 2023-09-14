import pytest

from backup.utils import Path


def provision_path():
    with Path.tempfile() as path:
        yield path
    assert not path.exists()


def provision_folder(path):
    path.unlink()
    path.mkdir()
    yield path
    path.rmtree()
    path.touch()


@pytest.fixture()
def path():
    yield from provision_path()


@pytest.fixture()
def path2():
    yield from provision_path()


@pytest.fixture()
def folder(path):
    yield from provision_folder(path)


@pytest.fixture()
def folder2(path2):
    yield from provision_folder(path2)


@pytest.fixture()
def encryption_path(path):
    with path.encrypted as encryption_path:
        yield encryption_path
    assert not encryption_path.exists()
