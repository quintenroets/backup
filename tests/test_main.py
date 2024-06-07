from unittest.mock import MagicMock, patch

from backup import main


@patch("backup.backups.backup.Backup.run_action")
def test_main(_: MagicMock) -> None:
    main()
