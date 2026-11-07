from unittest.mock import patch

from backup.context import context
from backup.models import Path, PathRule
from backup.utils.parser.config import parse_config
from backup.utils.parser.rules import RuleParser


def test_nested_include() -> None:
    parser = RuleParser(root=Path("/"), includes=[{"d/e": ["f"]}])
    rules = PathRule(Path("d/e/f"), include=True), PathRule(Path(), include=False)
    assert tuple(parser.parse()) == rules


def test_version_keyword() -> None:
    with Path.tempdir() as root:
        (root / "1").touch(mtime=1)
        (root / "2").touch()
        parser = RuleParser(root=root, includes=["__VERSION__"])
        assert PathRule(Path("2"), include=True) in parser.parse()


def test_exclude() -> None:
    parser = RuleParser(root=Path("/"), excludes=["a"])
    assert PathRule(Path("a"), include=False) in parser.parse()


def test_home_source() -> None:
    with Path.tempdir() as home, patch.object(Path, "HOME", home):
        sync = {"includes": [""], "source": "/HOME"}
        config = {"cache": home, "dest": home, "syncs": [sync]}
        assert next(parse_config(config)).source == home


def test_sub_check_path() -> None:
    with Path.tempdir() as path, patch.object(context, "sub_check_path", path):
        sync = {"includes": [""], "source": path.parent}
        parsed = next(parse_config({"cache": path, "dest": path, "syncs": [sync]}))
    assert parsed.source == path
    assert parsed.rules == [PathRule(Path(), include=True)]
