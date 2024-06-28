import os

from backup.backup import commands
from backup.models import Path


def test_substitute_username() -> None:
    key = "USERNAME"
    value = "name"
    os.environ[key] = "name"
    path = Path.remote / Path.HOME.relative_to(Path("/"))
    path_str = commands.Backup.substitute_correct_username(path)
    assert Path(path_str).name == value
    os.environ.pop(key)
