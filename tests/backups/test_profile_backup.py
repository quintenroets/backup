from backup import Backup
from backup.backups import profile
from backup.models import Path


def test_set_profile(mocked_backup: Backup) -> None:
    profile.Backup().apply_profile("dark")


def test_generate_path_rules(mocked_backup: Backup) -> None:
    backup = profile.Backup()
    directory = Path("dummy_directory")
    expected_paths = (directory / "out.txt", directory / "out2.txt")
    paths_to_create = (
        backup.source / expected_paths[0],
        backup.dest / expected_paths[1],
    )
    for path in paths_to_create:
        path.touch()
    paths = set(backup.generate_paths())
    assert paths == set(expected_paths)
