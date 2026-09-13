import os
from dataclasses import dataclass
from functools import cache

from package_utils.secrets_ import load_secret


@dataclass
class RcloneConfig:
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers: int = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"
    drive_import_formats: str = "docx, xlsx"


@cache
def load_rclone_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
        env["RCLONE_CONFIG_PASS"] = load_secret("rclone")
    return env
