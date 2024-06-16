from backup.context import Context
from backup.models import Path
from backup.utils.parser import Rules


def test_parser(test_context: Context) -> None:
    include_rules = [{"a": ["b", "c"]}, {"d/e/f": ["g", "h"]}, "HOME", "__VERSION__"]
    rules = Rules(include_rules, root=Path("/"))
    parsed_paths = list(rules.get_paths())
    expected_path = Path("a/b")
    assert expected_path in parsed_paths
