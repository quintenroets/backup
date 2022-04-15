from __future__ import annotations

from plib import Path as BasePath


class BasePath2(BasePath):
    # define here to make sure that all folders have this method

    @property
    def mtime(self):
        """
        only precision up to one second to decide which files have the same mtime
        cannot be too precise to avoid false positives
        remote filesystem also has limited precision
        """
        return int(super().mtime)

    @mtime.setter
    def mtime(self, time):
        BasePath.mtime.fset(self, time)


class Path(BasePath2):
    assets: Path = BasePath2.assets / "backup"
    paths = assets / "paths"
    syncs = paths / "syncs"
    ignore_names = paths / "ignore_names"
    ignore_patterns = paths / "ignore_patterns"
    paths_include = paths / "include"
    paths_include_pull = paths / "pull_include"
    paths_exclude = paths / "exclude"
    paths_volatile = paths / "volatile"

    timestamps = assets / "timestamps" / "timestamps"
    profiles = assets / "profiles"
    filters = assets / "filters"
    active_profile = profiles / "active"
    profile_paths = profiles / "paths"

    drive = BasePath2.docs / "Drive"
    browser_config = BasePath2.HOME / ".config" / "browser"

    exports = assets / "exports"

    backup_cache = BasePath2.HOME.parent / "backup"

    remote = BasePath2("backup:Home")
