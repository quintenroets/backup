import os

import cli
import pytest
from hypothesis import given, strategies
from test_backup import fill, slow_test_settings

from backup.backup import Backup
from backup.utils import Path


def fill_root(folder: Path, content: bytes, number: int = 0):
    path = folder / str(number)
    commands = ["tee", path]
    cli.run(*commands, input=content, root=True, text=False)


@pytest.fixture()
def root_folder(folder2):
    cli.run("sudo chown root:root", folder2)
    yield folder2
    user = os.getlogin()
    cli.run(f"sudo chown {user}:{user}", folder2)


@slow_test_settings
@given(content=strategies.binary(min_size=1), content2=strategies.binary(min_size=1))
def test_push(folder: Path, root_folder: Path, content: bytes, content2: bytes):
    fill(folder, content)
    fill_root(root_folder, content2)
    backup = Backup(folder, root_folder, quiet=True)
    backup.push()
    assert not backup.status().paths
