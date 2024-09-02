from collections.abc import Callable, Iterator

import pytest

from backup.models import Path
from backup.utils import check_setup


@pytest.fixture
def restore(directory: Path) -> Callable[[Path], Iterator[None]]:
    def _restore(restored_directory: Path) -> Iterator[None]:
        if restored_directory.exists():
            restored_directory.rename(directory, exist_ok=True)
        yield
        directory.rename(restored_directory, exist_ok=True)

    return _restore


@pytest.fixture
def restore_and_check(
    restore: Callable[[Path], Iterator[None]],
) -> Callable[[Path], Iterator[None]]:
    def _restore_and_check(restored_directory: Path) -> Iterator[None]:
        content_hash = restored_directory.content_hash
        yield from restore(restored_directory)
        assert restored_directory.content_hash == content_hash

    return _restore_and_check


@pytest.fixture
def restore_rclone_config_path(
    restore_and_check: Callable[[Path], Iterator[None]],
) -> Iterator[None]:
    yield from restore_and_check(Path.rclone_config.parent)


@pytest.mark.usefixtures("restore_rclone_config_path")
def test_rclone_config_download() -> None:
    Path.rclone_config.unlink(missing_ok=True)
    check_setup()
    assert Path.rclone_config.lines[0] == "# Encrypted rclone configuration File"
