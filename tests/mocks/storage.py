from typing import Any, cast

from backup import storage
from backup.models import Path
from package_utils.storage import CachedFileContent


class Defaults:
    @classmethod
    def create_include_rules(cls) -> list[str | dict[str, Any]]:
        return [""]

    @classmethod
    def create_exclude_rules(cls) -> list[str | dict[str, Any]]:
        paths = cls.create_profile_paths()
        return cast(list[str | dict[str, Any]], paths)

    @classmethod
    def create_profile_paths(cls) -> list[str]:
        return ["dummy.txt", "dummy_directory"]


class Storage(storage.Storage):
    includes: CachedFileContent[list[str | dict[str, Any]]] = CachedFileContent(
        Path.paths_include, default=Defaults.create_include_rules()
    )
    excludes: CachedFileContent[list[str | dict[str, Any]]] = CachedFileContent(
        Path.paths_exclude, default=Defaults.create_exclude_rules()
    )
    profile_paths: CachedFileContent[list[str]] = CachedFileContent(
        Path.profile_paths, default=Defaults.create_profile_paths()
    )
