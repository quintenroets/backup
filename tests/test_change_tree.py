import cli
import pytest

from backup.change_tree import (
    DiffRoots,
    calculate_diff,
    cutoff_marker,
    print_changes,
    render_diff,
)
from backup.models import BackupConfig, Change, ChangeType, Path
from backup.transfer_plan import TransferPlan


def render_diff_content(old_content: bytes, new_content: bytes) -> str:
    with Path.tempdir() as old, Path.tempdir() as new:
        (old / "file.txt").byte_content = old_content
        (new / "file.txt").byte_content = new_content
        content = render_diff("file.txt", DiffRoots(old, new))
    with cli.console.capture() as capture:
        cli.console.print(content)
    return capture.get()


def render_changes(backup_config: BackupConfig, changes: list[Change]) -> str:
    with cli.console.capture() as capture:
        print_changes(TransferPlan(backup_config, changes), None)
    return capture.get()


def test_cut_off_diff_ends_with_marker() -> None:
    diff = calculate_diff([], ["x"] * 21)
    assert diff.splitlines()[-1] == cutoff_marker


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [(b"\0old", b"\0new", "binary content"), (b"same", b"same", "identical content")],
)
def test_undiffable_content_is_marked(old: bytes, new: bytes, message: str) -> None:
    assert message in render_diff_content(old, new)


def test_hidden_change_count_is_shown(backup_config: BackupConfig) -> None:
    paths = [f"{number}.txt" for number in range(1001)]
    changes = [Change(path, ChangeType.created) for path in paths]
    assert f"{cutoff_marker} 1 more" in render_changes(backup_config, changes)


def test_creations_are_shown_before_modifications(backup_config: BackupConfig) -> None:
    changes = [
        Change("changed.txt", ChangeType.modified),
        Change("new.txt", ChangeType.created),
    ]
    output = render_changes(backup_config, changes)
    assert output.index("new.txt") < output.index("changed.txt")
