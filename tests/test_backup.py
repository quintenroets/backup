from unittest.mock import patch

import cli
import pytest

from backup.models import Action, BackupConfig, Change, ChangeType, Path
from backup.syncer import FileState
from backup.transfer_plan import TransferPlan
from tests.conftest import BackupSetup


def test_change_missing_from_the_remote_is_not_recorded(
    backup_config: BackupConfig,
) -> None:
    """A file that never reached the remote must be detected again next run."""
    observed = {"never_synced.txt": FileState(1.0, 1)}
    changes = [Change("never_synced.txt", ChangeType.created)]
    TransferPlan(backup_config, changes).record(observed, {})
    assert "never_synced.txt" not in backup_config.records


def test_declined_push(backup: BackupSetup) -> None:
    (backup.source / "file.txt").text = "content"
    with patch.object(cli, "confirm", return_value=False):
        changes = backup.push()
    assert not changes


@pytest.mark.parametrize("action", [Action.push, Action.pull])
def test_modification_and_deletion_propagate(
    backup: BackupSetup,
    action: Action,
) -> None:
    """A deleted record is found at any depth and cleared from both sides."""
    origin, target = backup.sides(action)
    relative = "nested/directory/file.txt"
    (origin / "0.txt").text = "content"
    (origin / relative).text = "content"
    backup.run(action)
    (origin / "0.txt").text = "changed"
    (origin / relative).unlink()
    changes = backup.run(action)
    types = [change.type for change in changes]
    assert types == [ChangeType.modified, ChangeType.deleted]
    assert (target / "0.txt").text == "changed"
    assert not (target / relative).exists()
    assert relative not in backup.records


def test_push_with_sync_state_under_the_source(backup: BackupSetup) -> None:
    """A run rewrites its own sync state, so one in scope would push itself forever."""
    (backup.source / "file.txt").text = "content"
    name = "sync-state.json"
    nested = backup.override(sync_state=str(backup.source / name))
    assert nested.push()
    assert not nested.push()
    assert not (nested.dest / name).exists()


@pytest.mark.parametrize("action", [Action.push, Action.pull])
def test_diff_adds_incoming_content(backup: BackupSetup, action: Action) -> None:
    origin, _ = backup.sides(action)
    (origin / "file.txt").text = "incoming"
    with cli.console.capture() as capture:
        backup.run(action, diff=True)
    assert "+incoming" in capture.get()


def test_newly_ignored_file_is_deleted_once(backup: BackupSetup) -> None:
    """The remote holds what is actively backed up, not a permanent archive."""
    relative = "cache/data.bin"
    (backup.source / relative).text = "content"
    backup.push()
    ignoring = backup.override(ignores={"names": ["cache"]})
    assert ignoring.push()
    assert not (ignoring.dest / relative).exists()
    assert not ignoring.push()


def test_directory_replaced_by_symlink_is_deleted_once(backup: BackupSetup) -> None:
    """A symlink is outside the tree, so its content is no longer backed up there."""
    (backup.source / "linked" / "file.txt").text = "content"
    backup.push()
    with Path.tempdir() as target:
        (backup.source / "linked").rename(target / "moved")
        (backup.source / "linked").symlink_to(target / "moved")
        assert backup.push()
        assert not backup.push()
    assert not (backup.dest / "linked" / "file.txt").exists()


@pytest.mark.parametrize("action", [Action.push, Action.pull])
@pytest.mark.parametrize(
    ("old", "new"),
    [("changed", "changed/file.txt"), ("changed/file.txt", "changed")],
)
def test_type_change_replaces_the_old_path(
    backup: BackupSetup,
    action: Action,
    old: str,
    new: str,
) -> None:
    (backup.source / old).text = "old"
    (backup.source / "sibling" / "file.txt").text = "sibling"
    backup.push()
    origin, target = backup.sides(action)
    (origin / "changed").remove()
    (origin / new).text = "new"
    assert backup.run(action)
    assert (target / new).text == "new"
    assert (target / "sibling" / "file.txt").text == "sibling"
    assert not backup.run(action)


def test_symlink_is_only_followed_as_the_sync_source(backup: BackupSetup) -> None:
    with Path.tempdir() as parent:
        linked = parent / "linked"
        linked.symlink_to(backup.source)
        linked_backup = backup.override(source=str(linked))
        (linked_backup.source / "file.txt").text = "content"
        (parent / "real").text = "content"
        (linked_backup.source / "link").symlink_to(parent / "real")
        changes = linked_backup.push()
        assert [change.path for change in changes] == ["file.txt"]
        assert (linked_backup.dest / "file.txt").exists()


def test_pull_flags_unsynced_local_changes_as_conflicts(backup: BackupSetup) -> None:
    """A pull overwrites the source file, so unsynced local edits must be flagged."""
    source_file = backup.source / "file.txt"
    source_file.text = "original"
    backup.push()
    source_file.text = "local edit"
    (backup.dest / "file.txt").text = "remote edit"
    (backup.dest / "new.txt").text = "new remote file"
    changes = backup.pull()
    conflicts = {change.path: change.conflict for change in changes}
    assert conflicts == {"file.txt": True, "new.txt": False}


def test_pull_stays_within_include_rules(backup: BackupSetup) -> None:
    narrowed = backup.override(syncs=[{"includes": ["included"]}])
    for root, content in ((backup.source, "local"), (backup.dest, "remote")):
        for name in ("included", "excluded"):
            (root / name / "file.txt").text = content
    changes = narrowed.pull()
    assert [change.path for change in changes] == ["included/file.txt"]
    assert (backup.source / "included" / "file.txt").text == "remote"
    assert (backup.source / "excluded" / "file.txt").text == "local"
