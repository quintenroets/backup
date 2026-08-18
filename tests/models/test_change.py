from backup.backup.models import Change, Changes, ChangeTypes, Path


def test_paths_are_ordered_by_change_type() -> None:
    """A creation is shown before a modification, whatever order they arrive in."""
    changes = Changes(
        [
            Change(Path("sub/file.txt"), ChangeTypes.modified),
            Change(Path("other.txt"), ChangeTypes.created),
        ],
    )
    assert changes.paths == [Path("other.txt"), Path("sub/file.txt")]


def test_absolute_paths_are_anchored_at_the_source() -> None:
    """A relative path is meaningless to a caller reacting to the change."""
    change = Change(Path("sub/file.txt"), ChangeTypes.created)
    changes = Changes([change], Path("/root"))
    assert changes.absolute_paths == [Path("/root/sub/file.txt")]
