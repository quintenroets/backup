import typing
from dataclasses import astuple, dataclass, field

from backup.syncer import FileState, Snapshot

from .path import Path


@dataclass
class SyncRecord:
    local: FileState = field(default_factory=FileState)
    remote: FileState = field(default_factory=FileState)


class SyncRecords(dict[str, SyncRecord]):
    """The records of one sync, addressed relative to the path it covers."""

    @property
    def local(self) -> Snapshot:
        return {relative: record.local for relative, record in self.items()}

    @property
    def remote(self) -> Snapshot:
        return {relative: record.remote for relative, record in self.items()}


SyncState = dict[str, SyncRecords]


def load_sync_state(path: Path) -> SyncState:
    content: dict[str, dict[str, list[typing.Any]]] = path.json if path.size else {}
    return {
        dest: SyncRecords(
            (key, SyncRecord(FileState(*values[:2]), FileState(*values[2:])))
            for key, values in records.items()
        )
        for dest, records in content.items()
    }


def save_sync_state(path: Path, sync_state: SyncState) -> None:
    temporary = Path(f"{path}.tmp")
    temporary.json = {
        dest: {
            key: astuple(record.local) + astuple(record.remote)
            for key, record in records.items()
        }
        for dest, records in sync_state.items()
    }
    temporary.replace(path)
