from backup.models import Path


def test_short_notation() -> None:
    assert Path("").short_notation


def test_includes_pull() -> None:
    assert Path.paths_include_pull
