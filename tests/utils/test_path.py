from backup.models import Path


def test_is_root() -> None:
    path = Path("/") / "etc" / "non-existing"
    assert path.is_root
