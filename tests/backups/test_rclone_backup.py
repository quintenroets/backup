from backup.backup.rclone import Rclone
from backup.models import Path


def test_status() -> None:
    rclone = Rclone()
    rclone.run("version")


def test_generate_substituted_paths() -> None:
    substituted = next(Rclone.generate_substituted_paths(Path.remote))
    assert substituted == Path.remote.name
