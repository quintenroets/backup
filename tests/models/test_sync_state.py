from backup.models import (
    Path,
    SyncRecord,
    SyncRecords,
    load_sync_state,
    save_sync_state,
)
from backup.syncer import FileState


def test_round_trip_keeps_syncs_apart() -> None:
    """Every sync's records share one file, saved once per run."""
    record = SyncRecord(FileState(1.5, 2), FileState(3.5, 4))
    sync_state = {
        "first": SyncRecords({"a.txt": record}),
        "second": SyncRecords({"b.txt": record}),
    }
    with Path.tempfile() as path:
        save_sync_state(path, sync_state)
        assert load_sync_state(path) == sync_state
