from unittest.mock import MagicMock, patch

from package_dev_utils.tests.args import no_cli_args

from backup.cli import entry_point


@no_cli_args
@patch("backup.backup.backup.Backup.push")
def test_entry_point(mocked_run: MagicMock) -> None:
    entry_point.entry_point()
    mocked_run.assert_called_once()
