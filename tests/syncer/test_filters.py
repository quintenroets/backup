from backup.models import Path
from backup.syncer import SyncConfig
from backup.syncer.filters import FiltersCreator

source = Path("/source")
dest = Path("/dest")


def test_create_filters_from_path() -> None:
    directory = Path("subpath")
    config = SyncConfig(source=source, dest=dest, directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"+ /{directory / '**'}", "- *"]


def test_create_filters_with_overlapping_source() -> None:
    config = SyncConfig(source=dest / "sub_path", dest=dest)
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == ["- /sub_path/**"]


def test_path_used() -> None:
    path = Path("dummy.txt")
    config = SyncConfig(source=source, dest=dest, path=path)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (path,)


def test_directory_used() -> None:
    directory = Path("dummy")
    config = SyncConfig(source=source, dest=dest, directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (directory / "**",)
