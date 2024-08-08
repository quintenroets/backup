from typing import Any

from package_utils.storage import CachedFileContent

from backup.models import Path


class Storage:
    number_of_paths: CachedFileContent[int] = CachedFileContent(
        Path.number_of_paths,
        default=0,
    )
    ignore_patterns: CachedFileContent[list[str]] = CachedFileContent(
        Path.ignore_patterns,
        default=[],
    )
    ignore_names: CachedFileContent[list[str]] = CachedFileContent(
        Path.ignore_names,
        default=[],
    )
    includes: CachedFileContent[list[str | dict[str, Any]]] = CachedFileContent(
        Path.paths_include,
        default=[],
    )
    excludes: CachedFileContent[list[str | dict[str, Any]]] = CachedFileContent(
        Path.paths_exclude,
        default=[],
    )
    profile_paths: CachedFileContent[list[str]] = CachedFileContent(
        Path.profile_paths,
        default=[],
    )
    active_profile: CachedFileContent[str] = CachedFileContent(
        Path.active_profile,
        default="light",
    )
