from unittest.mock import patch

import pytest
from backup.backup import commands, paths, rclone, root, syncer
from backup.backups import profile, remote
from backup.backups.cache import cache

backup_classes = [
    profile.Backup,
    remote.Backup,
    cache.Backup,
    commands.Backup,
    paths.Rclone,
    rclone.Rclone,
    root.Backup,
    syncer.Backup,
]


@pytest.mark.parametrize("backup_class", backup_classes)
def test_setup_trigger(backup_class: type[rclone.Rclone]) -> None:
    with patch("backup.utils.setup.check_setup") as mocked_setup:
        backup_class()
        mocked_setup.assert_called_once()
