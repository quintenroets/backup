import os

from backup.backup import commands
from backup.models import Path


def test_substitute_username() -> None:
    key = "USERNAME"
    value = "name"
    os.environ[key] = "name"
    path_str = commands.Backup.substitute_correct_username(Path.HOME)
    assert path_str == str(Path.HOME.with_name(value))
    os.environ.pop(key)
