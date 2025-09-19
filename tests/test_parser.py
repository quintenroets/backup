import pytest

from backup.models import Path
from backup.utils.parser.rules import RuleParser


@pytest.mark.usefixtures("test_context")
def test_parser() -> None:
    include_rules = [{"a": ["b", "c"]}, {"d/e/f": ["g", "h"]}, "HOME", "__VERSION__"]
    rules = RuleParser(root=Path("/"), includes=include_rules)
    parsed_paths = list(rules.get_paths())
    expected_path = Path("a/b")
    assert expected_path in parsed_paths
