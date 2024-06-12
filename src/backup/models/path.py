from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypeVar, cast

import superpathlib
from simple_classproperty import classproperty

if TYPE_CHECKING:
    from datetime import datetime

T = TypeVar("T", bound="Path")


class Path(superpathlib.Path):
    @property  # type: ignore
    # type : ignore
    def mtime(self) -> int:
        """
        Remote filesystem is only precise up to one second and mtime is used to compare
        files.
        """
        return int(super().mtime)

    @mtime.setter
    def mtime(self, value: int) -> None:
        superpathlib.Path.mtime.fset(self, value)  # type: ignore[attr-defined]

    @property
    def hash_path(self: T) -> T:
        hashes = self.hashes
        if self.is_relative_to(self.backup_cache):
            backup_root = Path("/")
            hashes = self.backup_cache / self.hashes.relative_to(backup_root)
        path = hashes / self.name
        return cast(T, path)

    @property
    def with_export_suffix(self: T) -> T:
        return self.with_suffix(".pdf")

    def extract_date(self, check_tag: bool = False) -> datetime:
        from datetime import datetime, timezone

        mtime = self.mtime

        use_tag = check_tag and self.exists() and self.is_relative_to(Path.backup_cache)
        if use_tag:
            tag = self.tag
            if tag:
                mtime = int(tag)

        date = datetime.fromtimestamp(mtime)
        return date.astimezone(timezone.utc)

    def has_date(self, date: datetime, check_tag: bool = False) -> bool:
        path_date = self.extract_date(check_tag=check_tag)
        return self.extract_date_tuple(date) == self.extract_date_tuple(path_date)

    @classmethod
    def extract_date_tuple(cls, date: datetime) -> tuple[int, ...]:
        # drive remote only minute precision and month range
        return date.month, date.day, date.hour, date.minute

    @property
    def is_root(self) -> bool:
        is_remote = self.parts[0].endswith(":")
        return not is_remote and not self.user_has_write_access()

    def user_has_write_access(self) -> bool:
        path = self
        while not path.exists():
            path = path.parent
        return os.access(path, os.W_OK)

    @property
    def short_notation(self: T) -> T:
        path = cast(Path, self)
        if not path.is_absolute():
            untyped_path = Path("/") / path
            path = cast(T, untyped_path)
        short_path = (
            path.relative_to(Path.HOME) if path.is_relative_to(Path.HOME) else path
        )
        return cast(T, short_path)

    @classmethod
    @classproperty
    def source_root(cls: type[T]) -> T:
        return cls(__file__).parent.parent

    @classmethod
    @classproperty
    def assets(cls: type[T]) -> T:
        path = cls.script_assets / cls.source_root.name
        return cast(T, path)

    @classmethod
    @classproperty
    def hashes(cls: type[T]) -> T:
        path = cls.assets / "hashes"
        return cast(T, path)

    @classmethod
    @classproperty
    def backup_cache(cls: type[T]) -> T:
        path = cls.assets / "cache"
        return cast(T, path)

    @classmethod
    @classproperty
    def config(cls: type[T]) -> T:
        path = cls.assets / "config"
        return cast(T, path)

    @classmethod
    @classproperty
    def rclone_command_config(cls: type[T]) -> T:
        path = cls.config / "rclone_commands.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def ignore_names(cls: type[T]) -> T:
        path = cls.config / "ignore_names.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def ignore_patterns(cls: type[T]) -> T:
        path = cls.config / "ignore_patterns.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def paths_include(cls: type[T]) -> T:
        path = cls.config / "include.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def paths_include_pull(cls: type[T]) -> T:
        path = cls.config / "pull_include.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def paths_exclude(cls: type[T]) -> T:
        path = cls.config / "exclude.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def harddrive_paths(cls: type[T]) -> T:
        path = cls.config / "harddrive.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def profile_paths(cls: type[T]) -> T:
        path = cls.config / "profiles.yaml"
        return cast(T, path)

    @classmethod
    @classproperty
    def number_of_paths(cls: type[T]) -> T:
        path = cls.assets / "volatile" / "number_of_paths"
        return cast(T, path)

    @classmethod
    @classproperty
    def profiles(cls: type[T]) -> T:
        path = cls.assets / "profiles"
        return cast(T, path)

    @classmethod
    @classproperty
    def active_profile(cls: type[T]) -> T:
        path = cls.profiles / "active.txt"
        return cast(T, path)

    @classmethod
    @classproperty
    def resume(cls: type[T]) -> T:
        path = cls.docs / "Drive" / "resume" / "Resume"
        return cast(T, path)

    @classmethod
    @classproperty
    def main_resume_pdf(cls: type[T]) -> T:
        path = cls.resume / "Resume Quinten Roets.pdf"
        return cast(T, path)

    @classmethod
    @classproperty
    def remote(cls: type[T]) -> T:
        return cls("backup:")

    @classmethod
    @classproperty
    def harddrive(cls: type[T]) -> T:
        path = cls("/") / "media" / cls.HOME.name / "Backup"
        return cast(T, path)

    @classmethod
    @classproperty
    def rclone_config(cls: type[T]) -> T:
        path = cls.HOME / ".config" / "rclone" / "rclone.conf"
        return cast(T, path)
