from collections.abc import Callable, Iterator

import pytest
from backup.backups import cache
from backup.models import Path
from backup.utils import check_setup


@pytest.fixture
def restore(folder: Path) -> Callable[[Path], Iterator[None]]:
    def _restore(restored_folder: Path) -> Iterator[None]:
        if restored_folder.exists():
            restored_folder.rename(folder, exist_ok=True)
        yield
        folder.rename(restored_folder, exist_ok=True)

    return _restore


@pytest.fixture
def restore_and_check(
    folder: Path, restore: Callable[[Path], Iterator[None]]
) -> Callable[[Path], Iterator[None]]:
    def _restore_and_check(restored_folder: Path) -> Iterator[None]:
        content_hash = restored_folder.content_hash
        yield from restore(restored_folder)
        assert restored_folder.content_hash == content_hash

    return _restore_and_check


@pytest.fixture
def restore_config_path(
    restore_and_check: Callable[[Path], Iterator[None]],
) -> Iterator[None]:
    yield from restore_and_check(Path.config)


@pytest.fixture
def restore_rclone_config_path(
    restore_and_check: Callable[[Path], Iterator[None]],
) -> Iterator[None]:
    yield from restore_and_check(Path.rclone_config.parent)


def test_config_download(restore_config_path: None) -> None:
    Path.config.rmtree(missing_ok=True)
    cache.Backup.check_config_path()
    assert Path.config.exists()


def test_rclone_config_download(restore_rclone_config_path: None) -> None:
    Path.rclone_config.unlink(missing_ok=True)
    check_setup(install=False)
    assert Path.rclone_config.lines[0] == "# Encrypted rclone configuration File"
