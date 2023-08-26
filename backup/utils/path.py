from __future__ import annotations

import os
import typing

from plib import Path as BasePath

if typing.TYPE_CHECKING:
    from datetime import datetime  # noqa: autoimport


class BasePath2(BasePath):
    # define here to make sure that all folders have this method

    @property
    def mtime(self):
        """
        Only precision up to one second to decide which files have the same mtime cannot
        be too precise to avoid false positives remote filesystem also has limited
        precision.
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
        return cls.assets / "cache"

    @property
    def hash_path(self):
        path = self.hashes / self.name
        if not self.is_relative_to(self.HOME):
            path = self.backup_cache / path.relative_to(self.HOME)
        return path

    @property
    def export(self):
        return self.with_suffix(".pdf")

    @property
    def date(self):
        from datetime import datetime, timezone  # noqa: autoimport, E402

        date = datetime.fromtimestamp(self.mtime)
        return date.astimezone(timezone.utc)

    def has_date(self, date: datetime):
        return self.extract_date_tuple(date) == self.extract_date_tuple(self.date)

    @classmethod
    def extract_date_tuple(cls, date: datetime):
        # drive remote only minute precision and month range
        return date.month, date.day, date.hour, date.minute

    def is_root(self):
        return not os.access(self, os.W_OK)


class Path(BasePath2):
    assets = BasePath2.assets
    config = assets / "config"
    ignore_names = config / "ignore_names.yaml"
    ignore_patterns = config / "ignore_patterns.yaml"
    paths_include = config / "include.yaml"
    paths_include_pull = config / "pull_include"
    paths_exclude = config / "exclude.yaml"
    harddrive_paths = config / "harddrive.yaml"
    profile_paths = config / "profiles.yaml"

    number_of_paths = assets / "volatile" / "number_of_paths"

    profiles = assets / "profiles"
    active_profile = profiles / "active.txt"

    resume = BasePath2.docs / "Drive" / "resume" / "Resume"

    remote = BasePath2("backup:")
    harddrive = BasePath2(f"/media/{BasePath2.HOME.name}/Backup")

    rclone_config = BasePath2.HOME / ".config" / "rclone" / "rclone.conf"
