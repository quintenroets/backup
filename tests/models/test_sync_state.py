from collections.abc import Iterator

import pytest

from backup.backup.models import Path, SyncRecord, SyncRecords, SyncState
from backup.backup.models.sync_state import temporary_suffix
from backup.syncer import FileState


@pytest.fixture
def sync_state_path() -> Iterator[Path]:
    with Path.tempfile() as path:
        yield path


def create_record() -> SyncRecord:
    return SyncRecord(FileState(1.5, 2), FileState(3.5, 4))


def create_scope(path: Path, prefix: str = "") -> SyncRecords:
    return SyncRecords(SyncState(path), Path(prefix))


def test_unsaved_update_does_not_reach_the_file(sync_state_path: Path) -> None:
    """A run that fails before saving leaves the last synced state in place."""
    create_scope(sync_state_path).update("file.txt", create_record())
    assert create_scope(sync_state_path).record("file.txt") is None


def test_missing_file_reads_as_an_empty_sync_state(sync_state_path: Path) -> None:
    """The bootstrap path: a lost sync state reports everything as created."""
    sync_state_path.unlink()
    assert not SyncState(sync_state_path).records


def test_prefix_isolation(sync_state_path: Path) -> None:
    sync_state = SyncState(sync_state_path)
    SyncRecords(sync_state, Path("prefix")).update("file.txt", create_record())
    other = SyncRecords(sync_state, Path("other"))
    assert other.record("file.txt") is None
    assert not list(other.relative_keys())
    matching = SyncRecords(sync_state, Path("prefix"))
    assert list(matching.relative_keys()) == ["file.txt"]


def test_remove(sync_state_path: Path) -> None:
    scope = create_scope(sync_state_path)
    scope.update("file.txt", create_record())
    scope.remove("file.txt")
    scope.remove("missing.txt")
    scope.file.save()
    assert create_scope(sync_state_path).record("file.txt") is None


def test_one_save_publishes_every_scope(sync_state_path: Path) -> None:
    """Scopes write into the same records, so a run saves once for all syncs."""
    sync_state = SyncState(sync_state_path)
    SyncRecords(sync_state, Path("first")).update("file.txt", create_record())
    SyncRecords(sync_state, Path("second")).update("file.txt", create_record())
    sync_state.save()
    reopened = SyncState(sync_state_path)
    assert SyncRecords(reopened, Path("first")).record("file.txt") == create_record()
    assert SyncRecords(reopened, Path("second")).record("file.txt") == create_record()


def test_save_publishes_through_a_temporary_file(sync_state_path: Path) -> None:
    """The rename is what makes a rewrite atomic, so nothing may be left behind."""
    sync_state = SyncState(sync_state_path)
    SyncRecords(sync_state).update("file.txt", create_record())
    sync_state.save()
    assert not Path(f"{sync_state_path}{temporary_suffix}").exists()
