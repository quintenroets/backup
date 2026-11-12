import json
from dataclasses import dataclass
from datetime import datetime

import cli

from backup.models import BackupConfig
from backup.path import Path
from backup.syncer import SyncConfig, Syncer


@dataclass
class CacheSyncer:
    backup_config: BackupConfig

    def sync_from_remote(self) -> None:
        path = str(self.backup_config.dest).split(":")[-1]
        with cli.status(f"Reading remote filesystem at {path}"):
            self.update_cache()

    def update_cache(self) -> None:
        backup = self.backup_config
        config = SyncConfig(backup.cache, backup.dest, backup.rules)
        remote_mtimes = list_mtimes(config)
        for path, mtime in remote_mtimes.items():
            cache_path = backup.cache / path
            if cache_path.mtime != mtime:
                source_path = backup.source / path
                if source_path.exists() and source_path.mtime == mtime:
                    source_path.copy_to(cache_path)
                else:
                    # change content and mtime to trigger update
                    cache_path.text = "" if source_path.size else " "
                    cache_path.touch(mtime=cache_path.mtime + 1)
        backup.cache.mkdir(parents=True, exist_ok=True)
        for path in list_mtimes(config.reversed).keys() - remote_mtimes:
            (backup.cache / path).unlink()


def list_mtimes(config: SyncConfig) -> dict[Path, int]:
    args = "lsjson", "-R", "--files-only", "--no-mimetype", config.dest
    return {
        Path(row["Path"]): int(datetime.fromisoformat(row["ModTime"]).timestamp())
        for row in json.loads(Syncer(config).capture_output(*args))
    }
