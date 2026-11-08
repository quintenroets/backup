from backup.models import Path


def test_is_root() -> None:
    assert Path("/etc/non-existing").is_root
