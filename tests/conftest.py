import os
import sys
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import patch

import cli
import pytest
import superpathlib

from backup.backup import run
from backup.backup.context import Options
from backup.backup.models import (
    Action,
    BackupConfig,
    Changes,
    Path,
    Scope,
    SyncRecords,
    SyncState,
)
from backup.syncer import PathRule, SyncConfig, Syncer


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
def _username() -> None:
    os.environ["USERNAME"] = (
        "runner" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
    )


@pytest.fixture(scope="session", autouse=True)
def _mocked_cli() -> Iterator[None]:
    with (
        patch.object(cli, "confirm", return_value=True),
        patch.object(cli.console, "clear"),
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
    def sync_state(self) -> SyncRecords:
        return SyncRecords(SyncState(Path(self.config["sync_state"])))

    def push(self, **options: Any) -> list[Changes]:
        return self.run(Action.push, **options)

    def pull(self, **options: Any) -> list[Changes]:
        return self.run(Action.pull, **options)

    def run(self, action: Action, **options: Any) -> list[Changes]:
        return run(self.config, Options(action=action, **options))

    def with_sync(self, sync: dict[str, Any]) -> "BackupSetup":
        """The same directories and sync state, seen through an edited config."""
        return BackupSetup({**self.config, "syncs": [sync]})


@contextmanager
def create_backup(
    sync: dict[str, Any],
    dest: str | None = None,
) -> Iterator[BackupSetup]:
    """A backup over throwaway directories, or into a sub path of the source."""
    with ExitStack() as stack:
        source = stack.enter_context(Path.tempdir())
        dest_path = (
            source / dest if dest is not None else stack.enter_context(Path.tempdir())
        )
        sync_state_path = stack.enter_context(Path.tempfile())
        stack.enter_context(patch("cli.track_progress", new=lambda *args, **_: args[0]))
        config = {
            "source": str(source),
            "dest": str(dest_path),
            "sync_state": str(sync_state_path),
            "syncs": [sync],
        }
        yield BackupSetup(config)


@pytest.fixture
def mocked_backup() -> Iterator[BackupSetup]:
    sync = {"includes": [""], "excludes": ["dummy.txt", "dummy_directory"]}
    with create_backup(sync) as backup:
        yield backup


@pytest.fixture
def mocked_backup_with_scoped_includes() -> Iterator[BackupSetup]:
    with create_backup({"includes": ["included"]}) as backup:
        roots = (backup.source, backup.dest)
        for root, content in zip(roots, ("local", "remote"), strict=True):
            for name in ("included", "excluded"):
                (root / name).mkdir(parents=True)
                (root / name / "file.txt").text = content
        yield backup


@pytest.fixture
def mocked_backup_with_nested_dest() -> Iterator[BackupSetup]:
    with create_backup({"includes": [""]}, dest="remote") as backup:
        yield backup


@pytest.fixture
def mocked_backup_with_filled_content(mocked_backup: BackupSetup) -> BackupSetup:
    fill_directories(mocked_backup.source, mocked_backup.dest)
    return mocked_backup


@pytest.fixture
def backup_config() -> Iterator[BackupConfig]:
    """A config over a throwaway source, scanned without ever reaching a remote."""
    with Path.tempdir() as source, Path.tempfile() as sync_state_path:
        yield BackupConfig(
            source=source,
            dest=Path("dest:"),
            sync_state=SyncRecords(SyncState(sync_state_path)),
            scope=Scope([PathRule(Path(), include=True)]),
        )


@pytest.fixture
def mocked_syncer(mocked_backup: BackupSetup) -> Syncer:
    config = SyncConfig(source=mocked_backup.source, dest=mocked_backup.dest)
    return Syncer(config)


@pytest.fixture
def mocked_syncer_with_filled_content(mocked_syncer: Syncer) -> Syncer:
    fill_directories(mocked_syncer.config.source, mocked_syncer.config.dest)
    return mocked_syncer


def fill_directories(
    source: superpathlib.Path,
    dest: superpathlib.Path,
    content: str = "content",
) -> None:
    for number in (0, 1):
        fill(source, content, number=number)
    content2 = content * 2
    for number in (0, 2):
        fill(dest, content2, number=number)


def fill(
    directory: superpathlib.Path,
    content: str = "content",
    number: int = 0,
) -> None:
    path = directory / f"{number}.txt"
    path.text = content
