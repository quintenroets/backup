from backup.backup.models import Path, Scope
from backup.syncer import PathRule, SyncConfig
from backup.syncer.filters import generate_filters, generate_rule_filters


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


def create_filters(config: SyncConfig) -> list[str]:
    return list(generate_filters(config))


def test_directory_covers_everything_under_it() -> None:
    directory = Path("subpath")
    filters = create_filters(create_config(directory=directory))
    assert filters == [f"+ /{directory / '**'}", "- *"]


def test_single_path_is_selected() -> None:
    path = Path("dummy.txt")
    assert create_filters(create_config(path=path)) == [f"+ /{path}", "- *"]


def test_paths_are_made_relative_to_the_source() -> None:
    config = SyncConfig(
        source=Path("/source"),
        dest=Path("/dest"),
        paths=[Path("/source/a.txt"), Path("b.txt")],
    )
    assert create_filters(config) == ["+ /a.txt", "+ /b.txt", "- *"]


def test_rules_match_paths_literally() -> None:
    """A rule path holding filter characters must not be read as a pattern."""
    scope = Scope([PathRule(Path("dir [a]"), include=True)])
    filters = list(generate_rule_filters(scope.deepest_first))
    assert filters == ["+ /dir \\[a\\]", "+ /dir \\[a\\]/**", "- *"]


def test_rendered_filters_are_used_verbatim() -> None:
    """An external caller renders its own filters, which nothing may reinterpret."""
    config = create_config(path=Path("ignored.txt"))
    config.filter_rules = ["+ /chosen.txt", "- *"]
    assert create_filters(config) == config.filter_rules


def test_rules_take_precedence_over_paths() -> None:
    """The remote listing is scoped by rules: a path selection cannot widen it."""
    config = SyncConfig(
        source=Path("/source"),
        dest=Path("/dest"),
        rules=[PathRule(Path(), include=True)],
        paths=[Path("a.txt")],
    )
    assert create_filters(config) == ["+ /**", "- *"]
