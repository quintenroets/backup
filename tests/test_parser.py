import pytest

from backup.models import Path
from backup.utils.parser import Rules


@pytest.mark.usefixtures("test_context")
def test_parser() -> None:
    include_rules = [{"a": ["b", "c"]}, {"d/e/f": ["g", "h"]}, "HOME", "__VERSION__"]
    rules = Rules(include_rules, root=Path("/"))
    parsed_paths = list(rules.get_paths())
    expected_path = Path("a/b")
    assert expected_path in parsed_paths
