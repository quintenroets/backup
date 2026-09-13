from unittest.mock import patch

import cli
import pytest

from backup.backup.models import (
    Action,
    BackupConfig,
    Change,
    Changes,
    ChangeTypes,
    Path,
)
from backup.backup.transfer_plan import TransferPlan
from backup.syncer import FileState
from tests.conftest import BackupSetup


def test_push(mocked_backup_with_filled_content: BackupSetup) -> None:
    verify_push(mocked_backup_with_filled_content)


def verify_push(backup: BackupSetup) -> None:
    changes = backup.push()
    assert any(changes)
    assert not any(backup.push())


def test_push_records_sync_state(
    mocked_backup_with_filled_content: BackupSetup,
) -> None:
    backup = mocked_backup_with_filled_content
    backup.push()
    record = backup.sync_state.record("0.txt")
    assert record is not None
    source_file = backup.source / "0.txt"
    assert record.local == FileState(source_file.mtime, source_file.size)


def test_push_deletion(mocked_backup_with_filled_content: BackupSetup) -> None:
    """A deleted record is found at any depth and cleared from both sides."""
    backup = mocked_backup_with_filled_content
    relative = "nested/directory/file.txt"
    nested = backup.source / relative
    nested.text = "content"
    backup.push()
    nested.unlink()
    changes = backup.push()
    assert [str(change.path) for change in changes[0]] == [relative]
    assert changes[0].changes[0].type == ChangeTypes.deleted
    assert not (backup.dest / relative).exists()
    assert backup.sync_state.record(relative) is None


def test_change_missing_from_the_remote_is_not_recorded(
    backup_config: BackupConfig,
) -> None:
    """A file that never reached the remote must be detected again next run."""
    local_state = FileState(1.0, 1)
    change = Change(Path("never_synced.txt"), ChangeTypes.created, local_state)
    changes = Changes([change])
    TransferPlan(backup_config, changes, Action.push).record()
    assert backup_config.sync_state.record("never_synced.txt") is None


def test_push_mixed_changes(mocked_backup_with_filled_content: BackupSetup) -> None:
    backup = mocked_backup_with_filled_content
    backup.push()
    (backup.source / "0.txt").text = "changed"
    (backup.source / "1.txt").unlink()
    changes = backup.push()
    types = [change.type for change in changes[0]]
    assert types == [ChangeTypes.modified, ChangeTypes.deleted]


def test_declined_push(mocked_backup_with_filled_content: BackupSetup) -> None:
    with patch.object(cli, "confirm", return_value=False):
        changes = mocked_backup_with_filled_content.push()
    assert not any(changes)


def test_push_with_diff(mocked_backup_with_filled_content: BackupSetup) -> None:
    backup = mocked_backup_with_filled_content
    source_file = backup.source / "0.txt"
    source_file.text = "line1\nline2\nline3\n"
    backup.push()
    source_file.text = "line1\nchanged\nline3\n"
    (backup.source / "1.txt").unlink()
    changes = backup.push(diff=True)
    assert any(changes)
    assert (backup.dest / "0.txt").text == source_file.text
    assert not (backup.dest / "1.txt").exists()


@pytest.fixture
def mocked_backup_with_include_path(
    mocked_backup_with_filled_content: BackupSetup,
) -> BackupSetup:
    sync = {
        "includes": ["", "0.txt"],
        "excludes": ["dummy.txt", "dummy_directory"],
    }
    return mocked_backup_with_filled_content.with_sync(sync)


def test_push_with_include_path(mocked_backup_with_include_path: BackupSetup) -> None:
    verify_push(mocked_backup_with_include_path)


def test_push_with_nested_dest(mocked_backup_with_nested_dest: BackupSetup) -> None:
    backup = mocked_backup_with_nested_dest
    (backup.source / "0.txt").text = "content"
    verify_push(backup)
    assert (backup.dest / "0.txt").exists()


def test_push_with_sync_state_under_the_source(
    mocked_backup_with_filled_content: BackupSetup,
) -> None:
    """A run rewrites its own sync state, so one in scope would push itself forever."""
    backup = mocked_backup_with_filled_content
    name = "sync-state.json"
    nested = BackupSetup({**backup.config, "sync_state": str(backup.source / name)})
    verify_push(nested)
    assert not (nested.dest / name).exists()


def test_pull(mocked_backup_with_filled_content: BackupSetup) -> None:
    backup = mocked_backup_with_filled_content
    changes = backup.pull()
    assert any(changes)
    for dest_file in backup.dest.rglob("*.txt"):
        source_file = backup.source / dest_file.relative_to(backup.dest)
        assert source_file.text == dest_file.text
    assert not any(backup.pull())


def test_pull_mixed_changes(mocked_backup_with_filled_content: BackupSetup) -> None:
    backup = mocked_backup_with_filled_content
    backup.pull()
    (backup.dest / "0.txt").text = "changed remotely"
    (backup.dest / "2.txt").unlink()
    changes = backup.pull()
    types = [change.type for change in changes[0]]
    assert types == [ChangeTypes.modified, ChangeTypes.deleted]
    assert (backup.source / "0.txt").text == "changed remotely"
    assert not (backup.source / "2.txt").exists()
    assert backup.sync_state.record("2.txt") is None


def test_pull_flags_unsynced_local_changes_as_conflicts(
    mocked_backup: BackupSetup,
) -> None:
    """A pull overwrites the source file, so unsynced local edits must be flagged."""
    backup = mocked_backup
    source_file = backup.source / "file.txt"
    source_file.text = "original"
    backup.push()
    source_file.text = "local edit"
    (backup.dest / "file.txt").text = "remote edit"
    (backup.dest / "new.txt").text = "new remote file"
    changes = backup.pull()
    conflicts = {str(change.path): change.conflict for change in changes[0]}
    assert conflicts == {"file.txt": True, "new.txt": False}


def test_pull_leaves_records_outside_narrowed_rules_alone(
    mocked_backup_with_filled_content: BackupSetup,
) -> None:
    """A record the rules stopped covering must not be pulled over local content."""
    backup = mocked_backup_with_filled_content
    backup.push()
    source_file = backup.source / "0.txt"
    source_file.text = "changed since the rules narrowed"
    narrowed = backup.with_sync({"includes": ["1.txt"]})
    assert not any(narrowed.pull())
    assert source_file.text == "changed since the rules narrowed"
    assert backup.sync_state.record("0.txt") is not None


def test_pull_stays_within_include_rules(
    mocked_backup_with_scoped_includes: BackupSetup,
) -> None:
    backup = mocked_backup_with_scoped_includes
    changes = backup.pull()
    assert [str(change.path) for change in changes[0]] == ["included/file.txt"]
    assert (backup.source / "included" / "file.txt").text == "remote"
    assert (backup.source / "excluded" / "file.txt").text == "local"


def test_push_stays_within_include_rules(
    mocked_backup_with_scoped_includes: BackupSetup,
) -> None:
    backup = mocked_backup_with_scoped_includes
    (backup.source / "included" / "file.txt").text = "changed"
    (backup.source / "excluded" / "file.txt").text = "changed"
    changes = backup.push()
    assert [str(change.path) for change in changes[0]] == ["included/file.txt"]
