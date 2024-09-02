from unittest.mock import MagicMock, patch

from package_dev_utils.tests.args import cli_args, no_cli_args
from superpathlib import Path

from backup.cli import entry_point, mount


@no_cli_args
@patch("backup.backups.backup.Backup.run_action")
def test_entry_point(mocked_run: MagicMock) -> None:
    entry_point.entry_point()
    mocked_run.assert_called_once()


@patch("cli.launch")
@patch("cli.run")
def test_mount_entry_point(mocked_run: MagicMock, mocked_launch: MagicMock) -> None:
    path = Path.tempfile(create=False)
    args = cli_args("--path", path / "subfolder")
    with path, args:
        mount.entry_point()
    mocked_run.assert_called()
    mocked_launch.assert_called_once()


@no_cli_args
@patch("cli.launch")
def test_mount_entry_point_without_path_specified(mocked_launch: MagicMock) -> None:
    with patch("cli.run"):
        mount.entry_point()
    mocked_launch.assert_called_once()
