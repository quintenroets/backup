from unittest.mock import MagicMock, patch

from backup.cli import entry_point, mount
from package_dev_utils.tests.args import no_cli_args


@no_cli_args
@patch("backup.backups.backup.Backup.run_action")
def test_entry_point(_: MagicMock) -> None:
    entry_point.entry_point()


@no_cli_args
@patch("cli.launch")
@patch("cli.run_commands")
def test_mount_entry_point(_: MagicMock, __: MagicMock) -> None:
    mount.entry_point()
