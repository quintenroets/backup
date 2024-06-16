from backup.backup.paths import Rclone
from backup.models import Path


def test_escape() -> None:
    path = Path("path/**")
    Rclone.escape(path)


def test_generate_path_rules() -> None:
    rclone = Rclone()
    rclone.folder = rclone.source / "subpath"
    rclone.create_filters()


def test_generate_path_rules_with_overlapping_source() -> None:
    rclone = Rclone()
    rclone.source = rclone.dest / "subpath"
    rclone.create_filters()
