from __future__ import annotations

from plib import Path as BasePath


class BasePath2(BasePath):
    # define here to make sure that all folders have this method

    @property
    def mtime(self):
        """Only precision up to one second to decide which files have the same
        mtime cannot be too precise to avoid false positives remote filesystem
        also has limited precision.
        """
        return int(super().mtime)

    @mtime.setter
    def mtime(self, time):
        BasePath.mtime.fset(self, time)

    @classmethod
    @property
    def assets(cls) -> BasePath2:  # noqa
        return cls.script_assets / "backup"

    @classmethod
    @property
    def hashes(cls) -> BasePath2:  # noqa
        return cls.assets / "hashes"

    @classmethod
    @property
    def backup_cache(cls) -> BasePath2:  # noqa
        return cls.HOME.parent / "backup"

    @property
    def hash_path(self):
        path = self.hashes / self.name
        if not self.is_relative_to(self.HOME):
            path = self.backup_cache / path.relative_to(self.HOME)
        return path

    @property
    def export(self):
        return self.with_suffix(".pdf")


class Path(BasePath2):
    assets = BasePath2.assets
    config = assets / "config"
    ignore_names = config / "ignore_names.yaml"
    ignore_patterns = config / "ignore_patterns.yaml"
    exclude_zip = config / "exclude_zip.yaml"
    paths_include = config / "include.yaml"
    paths_include_pull = config / "pull_include"
    paths_exclude = config / "exclude.yaml"
    paths_volatile = config / "volatile.yaml"
    harddrive_paths = config / "harddrive.yaml"
    profile_paths = config / "profiles.yaml"

    timestamps = assets / "timestamps" / "timestamps"
    profiles = assets / "profiles"
    filters = assets / "filters"
    active_profile = profiles / "active.txt"

    browser_config = BasePath2.HOME / ".config" / "browser"
    browser_config_folder = BasePath2.HOME / ".config" / "chromium" / "Default"
    resume = BasePath2.docs / "Drive" / "resume" / "Resume"

    remote = BasePath2("backup:Home")
    harddrive = BasePath2(f"/media/{BasePath2.HOME.name}/Backup")

    rclone_config = BasePath2.HOME / ".config" / "rclone" / "rclone.conf"
