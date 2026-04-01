from backup.backup import Backup
from backup.backup.cache.cache_syncer import CacheSyncer


def test_handle_cache_mismatch_missing_cache(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    source_file = config.source / "file.txt"
    source_file.text = "content"
    cache_path = config.cache / "file.txt"
    date = source_file.extract_date()

    CacheSyncer(config).handle_cache_mismatch(cache_path, date)

    assert cache_path.exists()
    assert cache_path.mtime == source_file.mtime


def test_handle_cache_mismatch_wrong_existing_cache(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    source_file = config.source / "file.txt"
    source_file.text = "content"
    cache_path = config.cache / "file.txt"
    cache_path.text = ""
    cache_path.touch(mtime=1)  # simulate old wrong placeholder
    date = source_file.extract_date()

    CacheSyncer(config).handle_cache_mismatch(cache_path, date)

    assert cache_path.mtime == source_file.mtime
