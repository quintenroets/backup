from __future__ import annotations

import assets
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

    @classmethod
    @property
    def assets(cls) -> BasePath2:
        return super(BasePath2, cls).assets / "backup"

    @classmethod
    @property
    def hashes(cls) -> BasePath2:
        return cls.assets / "hashes"

    @property
    def hash_path(self):
        return self.hashes / self.name


class Path(BasePath2):
    assets = BasePath2.assets
    paths = assets / "paths"
    syncs = paths / "syncs"
    ignore_names = paths / "ignore_names"
    ignore_patterns = paths / "ignore_patterns"
    exclude_zip = paths / "exclude_zip"
    paths_include = paths / "include"
    paths_include_pull = paths / "pull_include"
    paths_exclude = paths / "exclude"
    paths_volatile = paths / "volatile"
    harddrive_paths = paths / "harddrive.yaml"

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
    harddrive = BasePath2(f"/media/{BasePath2.HOME.name}/Backup")
