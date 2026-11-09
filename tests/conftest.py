import os
import sys
from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest

from backup.context import Storage
from backup.path import Path


@pytest.fixture(scope="session", autouse=True)
def isolated_session() -> Iterator[None]:
    with Path.tempfile() as config_path, Path.tempdir() as remote_directory:
        env = {
            "RCLONE_CONFIG": str(config_path),
            "RCLONE_CONFIG_BACKUPMASTER_TYPE": "alias",
            "RCLONE_CONFIG_BACKUPMASTER_REMOTE": str(remote_directory),
        }
        with (
            patch.dict(os.environ, env),
            patch.object(Storage, "number_of_paths", 0),
            patch.object(cli, "confirm", return_value=True),
            patch.object(sys.stdin, "isatty", return_value=True),
        ):
            os.environ.pop("RCLONE_PASSWORD_COMMAND", None)
            yield
