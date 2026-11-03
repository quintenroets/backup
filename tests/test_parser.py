import pytest

from backup.models import Config, Entries, Path
from backup.parser import (
    generate_owned_exclusions,
    generate_scoped_rules,
    parse_config,
    parse_rules,
)
from backup.syncer import PathRule, generate_filters
from tests.conftest import BackupSetup


def test_entries_expand_into_path_rules() -> None:
    includes: Entries = [{"a": ["b", "c"]}, {"d/e": ["f"]}]
    with Path.tempdir() as root:
        rules = parse_rules(root, includes, ["a/c"])
    assert rules == [
        PathRule(Path("a/b"), include=True),
        PathRule(Path("a/c"), include=True),
        PathRule(Path("d/e/f"), include=True),
        PathRule(Path("a/c"), include=False),
    ]


@pytest.mark.parametrize(
    ("includes", "excludes", "expected"),
    [
        ([""], ["a/b"], False),
        ([""], [""], True),
        ([""], ["a/b/c"], False),
    ],
)
def test_sub_check_root_follows_the_deepest_containing_rule(
    includes: Entries,
    excludes: Entries,
    *,
    expected: bool,
) -> None:
    sub_path = Path("a/b/c")
    parsed = parse_rules(Path("/"), includes, excludes)
    rules = generate_scoped_rules(parsed, sub_path)
    sub_path_rules = [rule for rule in rules if rule.path == sub_path]
    assert [rule.include for rule in sub_path_rules] == [expected]


def test_versioned_include_resolves_to_the_newest_match() -> None:
    """The newest match wins; a name matching nothing yields no rule at all."""
    with Path.tempdir() as root:
        for name, mtime in (("app-2", 2), ("app-1", 1)):
            (root / name).mkdir()
            (root / name).mtime = mtime
        entries: Entries = ["app-__VERSION__", "missing__VERSION__"]
        rules = parse_rules(root, entries, [])
    assert [str(rule.path) for rule in rules] == ["app-2"]


def test_nested_dest_is_excluded_in_both_directions(backup: BackupSetup) -> None:
    """A source walk and a remote listing must agree on what the dest covers."""
    config = backup.override(dest=str(backup.source / "remote")).parse()
    assert not config.scope.includes("remote/file.txt")
    filters = list(generate_filters(config.scope.deepest_first))
    assert filters[:2] == ["- /remote", "- /remote/**"]


@pytest.mark.parametrize(
    ("sub_path", "expected"),
    [
        (Path(), {".config/git", ".config/chromium/Default"}),
        (Path(".config/chromium"), {".config/chromium/Default"}),
    ],
)
def test_sub_check_narrows_the_home_scope(sub_path: Path, expected: set[str]) -> None:
    sync = {
        "includes": [{".config": ["git", {"chromium": ["Default"]}]}],
        "source": "/HOME",
    }
    config = Config.from_dict({"syncs": [sync]})
    parsed = next(parse_config(config, {}, Path.HOME / sub_path))
    assert parsed.source == Path.HOME
    assert {str(rule.path) for rule in parsed.scope.rules if rule.include} == expected


def test_repeated_name_walks_up_to_the_outermost_overlap() -> None:
    source = Path("/root/name")
    dest = source / "sub_path" / source.name
    exclusions = generate_owned_exclusions(source, dest, Path("/sync-state.json"))
    assert list(exclusions) == [PathRule(Path("sub_path"), include=False)]
