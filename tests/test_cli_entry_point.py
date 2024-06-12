from unittest.mock import MagicMock, patch

from package_dev_utils.tests.args import no_cli_args

from backup import cli


@no_cli_args
@patch("backup.backups.backup.Backup.run_action")
def test_entry_point(_: MagicMock) -> None:
    cli.entry_point()
