from collections.abc import Container, Iterator

from backup.backup.models import (
    Action,
    Change,
    ChangeType,
    ChangeTypes,
    Path,
    Scope,
    SyncRecords,
)
from backup.syncer import FileState


def calculate_change(
    records: SyncRecords,
    relative: str,
    observed: FileState | None,
    action: Action,
) -> Change | None:
    """What a transfer in this direction has to do about one path."""
    record = records.record(relative)
    if observed is not None:
        recorded = None if record is None else record.state(action)
        change_type = classify_change(recorded, observed)
        change = (
            None
            if change_type is None
            else create_change(relative, change_type, observed, action)
        )
    elif record is not None:
        change = Change(Path(relative), ChangeTypes.deleted)
    else:
        change = None
    return change


def classify_change(
    recorded: FileState | None,
    observed: FileState,
) -> ChangeType | None:
    if recorded is None:
        change_type = ChangeTypes.created
    elif recorded == observed:
        change_type = None
    else:
        change_type = ChangeTypes.modified
    return change_type


def create_change(
    relative: str,
    change_type: ChangeType,
    observed: FileState,
    action: Action,
) -> Change:
    path = Path(relative)
    return (
        Change(path, change_type, local_state=observed)
        if action == Action.push
        else Change(path, change_type, remote_state=observed)
    )


def generate_unobserved_records(
    records: SyncRecords,
    scope: Scope,
    observed: Container[str],
) -> Iterator[str]:
    """The recorded paths an enumeration never reached."""
    for relative in records.relative_keys():
        if relative not in observed and scope.includes(relative):
            yield relative
