from backup.rclone import RcloneConfig
from backup.rclone.filters import FiltersCreator
from backup.models import Path


def test_create_filters_from_path() -> None:
    directory = Path("subpath")
    config = RcloneConfig(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"+ /{directory / '**'}", "- *"]


def test_create_filters_with_overlapping_source() -> None:
    config = RcloneConfig()
    sub_path = "sub_path"
    config.source = config.dest / sub_path
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"- /{sub_path}/**", "+ *"]


def test_path_used() -> None:
    path = Path("dummy.txt")
    config = RcloneConfig(path=path)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (path,)


def test_directory_used() -> None:
    directory = Path("dummy")
    config = RcloneConfig(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (directory / "**",)
