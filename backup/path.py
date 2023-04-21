from __future__ import annotations

from plib import Path as BasePath


class BasePath2(BasePath):
    # define here to make sure that all folders have this method

    @property
    def mtime(self):
        """only precision up to one second to decide which files have the same
        mtime cannot be too precise to avoid false positives remote filesystem
        also has limited precision.
        """
        return int(super().mtime)

    @mtime.setter
    def mtime(self, time):
        BasePath.mtime.fset(self, time)

    @classmethod
    @property
    def assets(cls) -> BasePath2:
        return super().assets / "backup"

    @classmethod
    @property
    def hashes(cls) -> BasePath2:
        return cls.assets / "hashes"

    @classmethod
    @property
    def backup_cache(cls) -> BasePath2:
        return cls.HOME.parent / "backup"

    @property
    def hash_path(self):
        path = self.hashes / self.name
        if not self.is_relative_to(self.HOME):
            path = self.backup_cache / path.relative_to(self.HOME)
        return path


class Path(BasePath2):
    assets = BasePath2.assets
    paths = assets / "paths"
    syncs = paths / "syncs"
    ignore_names = paths / "ignore_names.yaml"
    ignore_patterns = paths / "ignore_patterns.yaml"
    exclude_zip = paths / "exclude_zip.yaml"
    paths_include = paths / "include.yaml"
    paths_include_pull = paths / "pull_include"
    paths_exclude = paths / "exclude.yaml"
    paths_volatile = paths / "volatile.yaml"
    harddrive_paths = paths / "harddrive.yaml"

    timestamps = assets / "timestamps" / "timestamps"
    profiles = assets / "profiles"
    filters = assets / "filters"
    active_profile = profiles / "active"
    profile_paths = profiles / "paths.yaml"

    drive = BasePath2.docs / "Drive"
    browser_config = BasePath2.HOME / ".config" / "browser"
    browser_config_folder = BasePath2.HOME / ".config" / "chromium" / "Default"

    exports = assets / "exports"

    remote = BasePath2("backup:Home")
    harddrive = BasePath2(f"/media/{BasePath2.HOME.name}/Backup")

    config = BasePath2.HOME / ".config" / "rclone" / "rclone.conf"
