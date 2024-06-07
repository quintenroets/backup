from collections.abc import Iterator

import cli
import pytest
from backup.backup import Backup
from backup.models import Path
from hypothesis import given, strategies

from tests.test_backup import fill, slow_test_settings


def fill_root(directory: Path, content: bytes, number: int = 0) -> None:
    path = directory / str(number)
    commands = ["tee", path]
    cli.run(*commands, input=content, root=True, text=False)


@pytest.fixture()
def root_directory(directory2: Path) -> Iterator[Path]:
    directory2.rmdir()
    cli.run("sudo mkdir", directory2)
    yield directory2
    cli.run("sudo rm -r", directory2)


@slow_test_settings
@given(content=strategies.binary(min_size=1), content2=strategies.binary(min_size=1))
def test_push(
    directory: Path, root_directory: Path, content: bytes, content2: bytes
) -> None:
    fill(directory, content)
    fill_root(root_directory, content2)
    backup = Backup(directory, root_directory)
    backup.push()
    assert not backup.capture_status().paths
