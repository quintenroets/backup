from unittest.mock import MagicMock, patch

from backup.cli import entry_point, mount
from package_dev_utils.tests.args import cli_args, no_cli_args
from superpathlib import Path


@no_cli_args
@patch("backup.backups.backup.Backup.run_action")
def test_entry_point(_: MagicMock) -> None:
    entry_point.entry_point()


@patch("cli.launch")
@patch("cli.run")
def test_mount_entry_point(_: MagicMock, __: MagicMock) -> None:
    with Path.tempfile(create=False) as path:
        with cli_args("--path", path):
            mount.entry_point()


@no_cli_args
@patch("cli.launch")
@patch("cli.run")
def test_mount_entry_point_without_path_specified(_: MagicMock, __: MagicMock) -> None:
    mount.entry_point()
