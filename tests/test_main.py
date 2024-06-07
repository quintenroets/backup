from unittest.mock import MagicMock, patch

from backup import main
from backup.context.context import Context


@patch("backup.backups.backup.Backup.run_action")
def test_main(_: MagicMock) -> None:
    main()


@patch("cli.open_urls")
def test_url_open(_: MagicMock, test_context: Context) -> None:
    main()
