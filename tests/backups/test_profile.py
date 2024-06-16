import collections

from backup import Backup
from backup.backups import profile


def test_set_profile(mocked_backup: Backup) -> None:
    profile.Backup().apply_profile("dark")


def test_generate_path_rules(mocked_backup: Backup) -> None:
    backup = profile.Backup()
    paths_to_create = (
        backup.source / "dummy_directory" / "out.txt",
        backup.dest / "dummy_directory" / "out2.txt",
    )
    for path in paths_to_create:
        path.touch()
    paths = backup.generate_paths()
    collections.deque(paths)
