from unittest.mock import patch

from backup.models import PathRule
from backup.parser import flatten, make_relative, parse_config, resolve_pattern
from backup.path import Path


def test_nested_entries() -> None:
    assert list(flatten([{"a/b": ["c"]}])) == [Path("a/b/c")]


def test_version_keyword() -> None:
    with Path.tempdir() as root:
        (root / "1").touch(mtime=1)
        (root / "2").touch()
        assert resolve_pattern(Path("__VERSION__"), root) == root / "2"


def test_exclude_precedes_parent_include() -> None:
    rules = [PathRule(Path("a"), include=True), PathRule(Path("a/b"), include=False)]
    assert next(make_relative(rules, Path())) == PathRule(Path("a/b"), include=False)


def test_home_source() -> None:
    with Path.tempdir() as home, patch.object(Path, "HOME", home):
        config = {"source": "/HOME", "dest": home, "syncs": [{"includes": [""]}]}
        assert next(parse_config(config, Path("/"))).source == home


def test_backup_root() -> None:
    with Path.tempdir() as path:
        config = {"source": path.parent, "dest": path, "syncs": [{"includes": [""]}]}
        parsed = next(parse_config(config, path))
    assert parsed.source == path
    assert parsed.rules == [PathRule(Path(), include=True)]
