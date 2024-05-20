from collections.abc import Iterator

import cli
import pytest
from backup.backup import Backup
from backup.models import Path
from hypothesis import given, strategies

from tests.test_backup import fill, slow_test_settings


def fill_root(folder: Path, content: bytes, number: int = 0) -> None:
    path = folder / str(number)
    commands = ["tee", path]
    cli.run(*commands, input=content, root=True, text=False)


@pytest.fixture()
def root_folder(folder2: Path) -> Iterator[Path]:
    folder2.rmdir()
    cli.run("sudo mkdir", folder2)
    yield folder2
    cli.run("sudo rm -r", folder2)


@slow_test_settings
@given(content=strategies.binary(min_size=1), content2=strategies.binary(min_size=1))
def test_push(folder: Path, root_folder: Path, content: bytes, content2: bytes) -> None:
    fill(folder, content)
    fill_root(root_folder, content2)
    backup = Backup(folder, root_folder)
    backup.push()
    assert not backup.capture_status().paths
