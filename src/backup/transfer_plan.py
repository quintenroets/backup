from dataclasses import dataclass

from .models import Action, BackupConfig, Change, ChangeType, Path, SyncRecord
from .syncer import Snapshot


@dataclass
class TransferPlan:
    config: BackupConfig
    changes: list[Change]

    @property
    def paths(self) -> list[str]:
        return [change.path for change in self.changes]

    @property
    def absolute_paths(self) -> list[Path]:
        return [self.config.source / path for path in self.paths]

    def apply(self, action: Action) -> None:
        transfers = self.select_paths(ChangeType.created, ChangeType.modified)
        deletions = self.select_paths(ChangeType.deleted)
        if deletions:
            parents = {parent for path in deletions for parent in Path(path).parents}
            replaced = [path for path in transfers if Path(path) in parents]
            self.config.create_syncer(deletions + replaced, action).delete()
        if transfers:
            self.config.create_syncer(transfers, action).push()
        remote = self.config.create_syncer(self.paths).list_remote_files()
        self.record(self.config.observe_local(self.paths), remote)

    def record(self, local: Snapshot, remote: Snapshot) -> None:
        records = self.config.records
        for relative in self.paths:
            if relative in local and relative in remote:
                records[relative] = SyncRecord(local[relative], remote[relative])
            else:
                records.pop(relative, None)

    def select_paths(self, *types: ChangeType) -> list[str]:
        return [change.path for change in self.changes if change.type in types]
