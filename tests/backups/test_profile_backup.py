import pytest

from backup.backups import profile
from backup.models import Path


@pytest.mark.usefixtures("context")
def test_set_profile() -> None:
    profile.Backup().apply_profile("dark")


@pytest.mark.usefixtures("test_context")
def test_generate_path_rules() -> None:
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


@pytest.mark.usefixtures("test_context")
def test_reload() -> None:
    profile.Backup().reload()


@pytest.mark.usefixtures("test_context_with_sub_check_path")
def test_sub_check_path_ignored() -> None:
    profile.Backup().push()
