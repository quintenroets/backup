import pytest

from backup.backup.models import Config, Entries, Path, SyncState
from backup.backup.parser import parse_config, parse_rules
from backup.syncer.filters import generate_rule_filters
from tests.conftest import BackupSetup


def test_parser() -> None:
    include_rules = [{"a": ["b", "c"]}, {"d/e/f": ["g", "h"]}, "HOME", "__VERSION__"]
    rules = parse_rules(Path("/"), Path(""), include_rules, [])
    parsed_paths = [rule.path for rule in rules]
    expected_path = Path("a/b")
    assert expected_path in parsed_paths


@pytest.mark.parametrize(
    ("includes", "excludes", "expected"),
    [([""], ["a/b"], False), (["a/b"], [""], True), ([""], [""], True)],
)
def test_sub_check_root_follows_the_deepest_containing_rule(
    includes: Entries,
    excludes: Entries,
    *,
    expected: bool,
) -> None:
    rules = parse_rules(Path("/"), Path("a/b/c"), includes, excludes)
    root_rules = [rule for rule in rules if not rule.depth]
    assert [rule.include for rule in root_rules] == [expected]


def test_versioned_include_without_match_covers_nothing() -> None:
    """A __VERSION__ entry naming nothing on disk yields no rule at all."""
    with Path.tempdir() as root:
        rules = parse_rules(root, Path(""), ["missing__VERSION__"], [])
    assert [rule.depth for rule in rules] == [0]


def test_nested_dest_is_excluded_in_both_directions(
    mocked_backup_with_nested_dest: BackupSetup,
) -> None:
    """A source walk and a remote listing must agree on what the dest covers."""
    serialized = Config.from_dict(mocked_backup_with_nested_dest.config)
    config = next(parse_config(serialized, SyncState(Path(serialized.sync_state))))
    assert not config.scope.includes("remote/file.txt")
    filters = list(generate_rule_filters(config.scope.deepest_first))
    assert filters[:2] == ["- /remote", "- /remote/**"]


def test_config_parser() -> None:
    verify_config_parser()


def test_config_parser_with_sub_check_path() -> None:
    verify_config_parser(Path.HOME / ".config")


def verify_config_parser(sub_check_path: Path | None = None) -> None:
    sync = {
        "includes": [{".config": ["git", {"chromium": ["Default"]}]}],
        "excludes": [""],
        "source": "/HOME",
    }
    config = Config.from_dict({"syncs": [sync]})
    sync_state = SyncState(Path(config.sync_state))
    parsed_config = list(parse_config(config, sync_state, sub_check_path))
    assert parsed_config
