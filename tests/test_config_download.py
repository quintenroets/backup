import pytest

from backup.backups import cache
from backup.utils import Path, check_setup


@pytest.fixture
def restore(folder: Path):
    def _restore(restored_folder: Path):
        if restored_folder.exists():
            restored_folder.rename(folder, exist_ok=True)
        yield
        folder.rename(restored_folder, exist_ok=True)

    return _restore


@pytest.fixture
def restore_and_check(folder: Path, restore):
    def _restore_and_check(restored_folder: Path):
        content_hash = restored_folder.content_hash
        yield from restore(restored_folder)
        assert restored_folder.content_hash == content_hash

    return _restore_and_check


@pytest.fixture
def restore_config_path(restore_and_check):
    yield from restore_and_check(Path.config)


@pytest.fixture
def restore_rclone_config_path(restore_and_check):
    yield from restore_and_check(Path.rclone_config.parent)


def test_config_download(restore_config_path):
    Path.config.rmtree()
    cache.Backup.check_config_path()
    assert Path.config.exists()


def test_rclone_config_download(restore_rclone_config_path):
    Path.rclone_config.unlink(missing_ok=True)
    check_setup(install=False)
    assert Path.config.exists()
