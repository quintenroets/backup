from __future__ import annotations

import os
import typing

import plib

if typing.TYPE_CHECKING:
    from datetime import datetime  # noqa: autoimport


class BasePath(plib.Path):
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
        plib.Path.mtime.fset(self, time)

    @classmethod
    @property
    def assets(cls) -> BasePath:  # noqa
        return cls.script_assets / "backup"

    @classmethod
    @property
    def hashes(cls) -> BasePath:  # noqa
        return cls.assets / "hashes"

    @classmethod
    @property
    def backup_cache(cls) -> BasePath:  # noqa
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

    def get_date(self, check_tag=False):
        from datetime import datetime, timezone  # noqa: autoimport, E402

        mtime = self.mtime

        use_tag = check_tag and self.exists() and self.is_relative_to(Path.backup_cache)
        if use_tag:  # noqa
            tag = self.tag
            if tag:
                mtime = int(tag)

        date = datetime.fromtimestamp(mtime)
        return date.astimezone(timezone.utc)

    def has_date(self, date: datetime, check_tag=False):
        path_date = self.get_date(check_tag=check_tag)
        return self.extract_date_tuple(date) == self.extract_date_tuple(path_date)

    @classmethod
    def extract_date_tuple(cls, date: datetime):
        # drive remote only minute precision and month range
        return date.month, date.day, date.hour, date.minute

    def is_root(self):
        is_remote = self.parts[0].endswith(":")
        return not is_remote and not self.user_has_write_access()

    def user_has_write_access(self):
        path = self
        while not path.exists():
            path = path.parent
        return os.access(path, os.W_OK)

    @property
    def short_notation(self):
        path = self
        if not path.is_absolute():
            path = Path("/") / path
        return path.relative_to(Path.HOME) if path.is_relative_to(Path.HOME) else path


class Path(BasePath):
    assets = BasePath.assets
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

    resume = BasePath.docs / "Drive" / "resume" / "Resume"
    main_resume_pdf = resume.parent / "Resume Quinten Roets.pdf"

    remote = BasePath("backup:")
    harddrive = BasePath(f"/media/{BasePath.HOME.name}/Backup")

    rclone_config = BasePath.HOME / ".config" / "rclone" / "rclone.conf"
