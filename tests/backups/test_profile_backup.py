from backup.backups import profile
from backup.context import Context
from backup.models import Path


def test_set_profile(context: Context) -> None:
    profile.Backup().apply_profile("dark")


def test_generate_path_rules(test_context: Context) -> None:
    backup = profile.Backup()
    directory = Path("dummy_directory")
    expected_paths = (directory / "out.txt", directory / "out2.txt", Path("dummy.txt"))
    paths_to_create = (
        backup.source / expected_paths[0],
        backup.dest / expected_paths[1],
        backup.source / expected_paths[2],
    )
    for path in paths_to_create:
        path.touch()
    paths = set(backup.generate_paths())
    assert paths == set(expected_paths)


def test_reload(test_context: Context) -> None:
    profile.Backup().reload()


def test_sub_check_path_ignored(test_context_with_sub_check_path: Context) -> None:
    profile.Backup().push()
