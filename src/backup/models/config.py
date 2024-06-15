from dataclasses import dataclass

from .path import Path


@dataclass
class Config:
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"  # handle largest files first
    drive_import_formats = "docx, xlsx"
    max_backup_size: int = int(50e6)
    browser_name: str = "chromium"
    browser_folder: Path = Path(".config") / browser_name
    browser_pattern: str = f"{browser_folder}/**/*"
    backup_source: Path = Path.backup_source
    backup_dest: Path = Path.remote
    cache_path: Path = Path.backup_cache
    profiles_source_root: Path = Path.HOME
