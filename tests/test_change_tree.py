from unittest.mock import patch

import cli

from backup.backup.change_tree import (
    ChangeTree,
    DiffRoots,
    binary_message,
    calculate_diff,
    create_diff_content,
    cutoff_marker,
    identical_message,
)
from backup.backup.models import Change, Changes, ChangeTypes, Path


def render_diff_content(source_content: bytes, staging_content: bytes) -> str:
    with Path.tempdir() as source, Path.tempdir() as staging:
        (source / "file.txt").byte_content = source_content
        (staging / "file.txt").byte_content = staging_content
        content = create_diff_content(Path("file.txt"), DiffRoots(source, staging))
    with cli.console.capture() as capture:
        cli.console.print(content)
    return capture.get()


def test_cut_off_diff_ends_with_marker() -> None:
    with patch("backup.backup.change_tree.max_diff_lines_per_file", 2):
        diff = calculate_diff(["a", "b", "c"], ["x", "y", "z"])
    assert diff.splitlines() == ["@@ -1,3 +1,3 @@", "-a", cutoff_marker]


def test_binary_content_is_marked() -> None:
    assert binary_message in render_diff_content(b"\x00new", b"\x00old")


def test_identical_content_is_marked() -> None:
    assert identical_message in render_diff_content(b"same", b"same")


def test_hidden_change_count_is_shown() -> None:
    paths = [Path(f"{number}.txt") for number in range(3)]
    changes = Changes([Change(path, ChangeTypes.created) for path in paths])
    with patch("backup.backup.change_tree.max_changes_shown", 2):
        structure = ChangeTree.from_changes(changes)
    with cli.console.capture() as capture:
        structure.print(None)
    assert f"{cutoff_marker} 1 more" in capture.get()
