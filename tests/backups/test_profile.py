from backup import Backup
from backup.backups import profile


def test_set_profile(mocked_backup: Backup) -> None:
    profile.Backup().apply_profile("dark")
