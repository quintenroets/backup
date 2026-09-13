from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from typing import Self

from backup.syncer import FileState, Syncer

from .models import Action, BackupConfig, Change, Changes, ChangeTypes, Path, SyncRecord


@dataclass
class TransferPlan:
    backup_config: BackupConfig
    changes: Changes
    action: Action

    @classmethod
    def from_changes(
        cls,
        backup_config: BackupConfig,
        changes: list[Change],
        action: Action,
    ) -> Self:
        return cls(backup_config, Changes(changes, backup_config.source), action)

    def apply(self) -> None:
        syncer = self.create_syncer(self.changes.paths)
        if self.action == Action.push:
            syncer.push()
            self.fill_remote_states()
        else:
            syncer.pull()
            self.fill_local_states()
        self.record()

    def fill_remote_states(self) -> None:
        remote_files = self.fetch_remote_files()
        for change in self.transferred_changes():
            change.remote_state = remote_files.get(str(change.path))

    def fill_local_states(self) -> None:
        for change in self.transferred_changes():
            change.local_state = FileState.read(
                self.backup_config.source / change.path,
            )

    def fetch_remote_files(self) -> dict[str, FileState]:
        paths = [change.path for change in self.transferred_changes()]
        return self.create_syncer(paths).list_remote_files() if paths else {}

    def transferred_changes(self) -> Iterator[Change]:
        return (change for change in self.changes if change.type != ChangeTypes.deleted)

    def record(self) -> None:
        for change in self.changes:
            relative = str(change.path)
            if change.type == ChangeTypes.deleted:
                self.backup_config.sync_state.remove(relative)
            elif change.local_state is not None and change.remote_state is not None:
                record = SyncRecord(change.local_state, change.remote_state)
                self.backup_config.sync_state.update(relative, record)

    def create_syncer(self, paths: Sequence[Path]) -> Syncer:
        return self.backup_config.create_syncer(
            self.backup_config.sync_config.with_paths(paths),
        )
