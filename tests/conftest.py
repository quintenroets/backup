import os
import sys
from collections.abc import Iterator
from dataclasses import dataclass, replace
from typing import Any, Self
from unittest.mock import patch

import cli
import pytest

from backup import run_config
from backup.context import Options
from backup.models import (
    Action,
    BackupConfig,
    Change,
    Config,
    Path,
    SyncRecords,
    load_sync_state,
)
from backup.parser import parse_config


@pytest.fixture(scope="session", autouse=True)
def _rclone_test_config() -> Iterator[None]:
    os.environ.pop("RCLONE_PASSWORD_COMMAND", None)
    with Path.tempfile() as config_path, Path.tempdir() as remote_directory:
        config = {
            "RCLONE_CONFIG": str(config_path),
            "RCLONE_CONFIG_BACKUPMASTER_TYPE": "alias",
            "RCLONE_CONFIG_BACKUPMASTER_REMOTE": str(remote_directory),
        }
        os.environ.update(config)
        yield


@pytest.fixture(scope="session", autouse=True)
def _mocked_cli() -> Iterator[None]:
    with (
        patch.object(cli, "confirm", return_value=True),
        patch.object(sys.stdin, "isatty", return_value=True),
    ):
        yield


@dataclass
class BackupSetup:
    """A backup over throwaway directories, driven through the public entry point."""

    config: dict[str, Any]

    @property
    def source(self) -> Path:
        return Path(self.config["source"])

    @property
    def dest(self) -> Path:
        return Path(self.config["dest"])

    @property
    def records(self) -> SyncRecords:
        return load_sync_state(Path(self.config["sync_state"]))[""]

    def sides(self, action: Action) -> tuple[Path, Path]:
        sides = (self.source, self.dest)
        return sides if action == Action.push else sides[::-1]

    def override(self, **config: Any) -> Self:
        return replace(self, config={**self.config, **config})

    def parse(self) -> BackupConfig:
        return next(parse_config(Config.from_dict(self.config), {}, None))

    def push(self) -> list[Change]:
        return self.run(Action.push)

    def pull(self) -> list[Change]:
        return self.run(Action.pull)

    def run(self, action: Action, *, diff: bool = False) -> list[Change]:
        plans = run_config(Config.from_dict(self.config), Options(action, diff=diff))
        return [change for plan in plans for change in plan.changes]


@pytest.fixture
def backup() -> Iterator[BackupSetup]:
    with Path.tempdir() as source, Path.tempdir() as dest, Path.tempfile() as state:
        config = {
            "source": str(source),
            "dest": str(dest),
            "sync_state": str(state),
            "syncs": [{"includes": [""]}],
            "rclone": {"retries": 1, "retries_sleep": "0s"},
        }
        yield BackupSetup(config)


@pytest.fixture
def backup_config(backup: BackupSetup) -> BackupConfig:
    return backup.parse()
