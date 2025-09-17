from backup.models import Path


def test_short_notation() -> None:
    assert Path("").short_notation
