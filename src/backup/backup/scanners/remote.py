from collections.abc import Iterator
from itertools import chain

import cli

from backup.backup.models import Action, BackupConfig, Change, ChangeTypes, Path
from backup.backup.transfer_plan import TransferPlan
from backup.syncer import FileState

from .change_calculation import calculate_change, generate_unobserved_records


def scan_remotes(backup_configs: list[BackupConfig]) -> list[TransferPlan]:
    return [scan_remote(config) for config in backup_configs]


def scan_remote(config: BackupConfig) -> TransferPlan:
    remote_files = read_remote_files(config)
    changes = list(generate_changes(config, remote_files))
    return TransferPlan.from_changes(config, changes, Action.pull)


def read_remote_files(config: BackupConfig) -> dict[str, FileState]:
    remote_path = str(config.dest).split(":")[-1]
    with cli.status(f"Reading remote filesystem at {remote_path}"):
        return config.create_syncer().list_remote_files()


def generate_changes(
    config: BackupConfig,
    remote_files: dict[str, FileState],
) -> Iterator[Change]:
    changes = chain(
        generate_listed_changes(config, remote_files),
        generate_deletions(config, remote_files),
    )
    for change in changes:
        if not config.scope.ignored(str(change.path)):
            change.conflict = detect_local_modification(config, change)
            yield change


def generate_listed_changes(
    config: BackupConfig,
    remote_files: dict[str, FileState],
) -> Iterator[Change]:
    for relative, state in remote_files.items():
        change = calculate_change(config.sync_state, relative, state, Action.pull)
        if change is not None:
            yield change


def generate_deletions(
    config: BackupConfig,
    remote_files: dict[str, FileState],
) -> Iterator[Change]:
    records = config.sync_state
    for relative in generate_unobserved_records(records, config.scope, remote_files):
        yield Change(Path(relative), ChangeTypes.deleted)


def detect_local_modification(config: BackupConfig, change: Change) -> bool:
    record = config.sync_state.record(str(change.path))
    recorded = None if record is None else record.local
    observed = FileState.observe(f"{config.source}/{change.path}")
    return observed is not None and observed != recorded
