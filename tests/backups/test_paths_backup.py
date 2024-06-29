from backup.backup.paths import Rclone
from backup.models import Path


def test_escape() -> None:
    path = Path("path/**")
    Rclone.escape(path)


def test_generate_path_rules() -> None:
    directory = Path("subpath")
    rclone = Rclone(directory=directory)
    rclone.create_filters()
    assert rclone.filter_rules == [f"+ /{directory / '**'}", "- *"]


def test_generate_path_rules_with_overlapping_source() -> None:
    rclone = Rclone()
    sub_path = "sub_path"
    rclone.source = rclone.dest / sub_path
    rclone.create_filters()
    assert rclone.filter_rules == [f"- /{sub_path}/**", "+ *"]
