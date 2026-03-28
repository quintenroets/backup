from backup.models import Path
from backup.syncer import SyncConfig
from backup.syncer.filters import FiltersCreator


def create_config(
    path: Path | None = None,
    directory: Path | None = None,
) -> SyncConfig:
    return SyncConfig(
        source=Path("/source"),
        dest=Path("/dest"),
        path=path,
        directory=directory,
    )


def test_create_filters_from_path() -> None:
    directory = Path("subpath")
    config = create_config(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == [f"+ /{directory / '**'}", "- *"]


def test_create_filters_with_overlapping_source() -> None:
    config = SyncConfig(source=Path("/dest") / "sub_path", dest=Path("/dest"))
    FiltersCreator(config).create_filters_from_paths()
    assert config.filter_rules == ["- /sub_path/**"]


def test_path_used() -> None:
    path = Path("dummy.txt")
    config = create_config(path=path)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (path,)


def test_directory_used() -> None:
    directory = Path("dummy")
    config = create_config(directory=directory)
    FiltersCreator(config).create_filters_from_paths()
    assert config.paths == (directory / "**",)
