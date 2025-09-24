from unittest.mock import patch

import pytest

from backup.context import Context
from backup.models import Path
from backup.utils.parser.config import parse_config
from backup.utils.parser.rules import RuleParser


@pytest.mark.usefixtures("test_context")
def test_parser() -> None:
    include_rules = [{"a": ["b", "c"]}, {"d/e/f": ["g", "h"]}, "HOME", "__VERSION__"]
    rules = RuleParser(root=Path("/"), includes=include_rules)
    parsed_paths = list(rules.get_paths())
    expected_path = Path("a/b")
    assert expected_path in parsed_paths


def test_config_parser() -> None:
    verify_config_parser()


def test_config_parser_with_sub_check_path(test_context: Context) -> None:
    sub_check_path = Path.HOME / ".config"
    with patch.object(test_context, "sub_check_path", sub_check_path):
        verify_config_parser()


def verify_config_parser() -> None:
    sync = {
        "includes": [{".config": ["git", {"chromium": ["Default"]}]}],
        "excludes": [""],
        "source": "/HOME",
        "dest": "/__PROFILE__",
    }
    config = {"syncs": [sync]}
    parsed_config = list(parse_config(config))
    assert parsed_config
