from typing import Any

from package_utils.storage import CachedFileContent

from backup.models import Path


class Storage:
    number_of_paths: CachedFileContent[int] = CachedFileContent(
        Path.number_of_paths,
        default=0,
    )
    backup_config: CachedFileContent[list[Any]] = CachedFileContent(
        Path.backup_config,
        default=[],
    )
