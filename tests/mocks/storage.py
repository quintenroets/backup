from typing import Any

from backup import storage
from backup.models import Path
from package_utils.storage import CachedFileContent


class Defaults:
    @classmethod
    def create_include_rules(cls) -> list[str | dict[str, Any]]:
        return [""]


class Storage(storage.Storage):
    includes: CachedFileContent[list[str | dict[str, Any]]] = CachedFileContent(
        Path.paths_include, default=Defaults.create_include_rules()
    )