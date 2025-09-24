from backup.models import Path
from backup.syncer import SyncConfig
from backup.syncer.filters import FiltersCreator


def test_create_filters_from_path() -> None:
    directory = Path("subpath")
    config = SyncConfig(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"+ /{directory / '**'}", "- *"]


def test_create_filters_with_overlapping_source() -> None:
    config = SyncConfig()
    sub_path = "sub_path"
    config.source = config.dest / sub_path
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"- /{sub_path}/**"]


def test_path_used() -> None:
    path = Path("dummy.txt")
    config = SyncConfig(path=path)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (path,)


def test_directory_used() -> None:
    directory = Path("dummy")
    config = SyncConfig(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (directory / "**",)
