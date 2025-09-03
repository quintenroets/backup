from __future__ import annotations

import os
from typing import TYPE_CHECKING, TypeVar, cast

import superpathlib
from simple_classproperty import classproperty
from typing_extensions import Self

if TYPE_CHECKING:
    from datetime import datetime  # pragma: nocover

T = TypeVar("T", bound="Path")


class Path(superpathlib.Path):
    @property
    def canonicalized(self) -> Self:
        return (
            Path.canonicalized_home / self.relative_to(Path.relative_home)
            if self.is_relative_to(Path.relative_home)
            else self
        )

    @property
    def decanonicalized(self) -> Self:
        return (
            Path.relative_home / self.relative_to(Path.canonicalized_home)
            if self.is_relative_to(Path.canonicalized_home)
            else self
        )

    @property  # type: ignore[override]
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
    def with_export_suffix(self) -> Self:
        return self.with_suffix(".pdf")

    def extract_date(self, *, check_tag: bool = False) -> datetime:
        from datetime import datetime, timezone

        mtime = self.mtime

        use_tag = check_tag and self.exists() and self.is_relative_to(Path.backup_cache)
        if use_tag:  # pragma: nocover
            tag = self.tag
            if tag:
                mtime = int(tag)

        return datetime.fromtimestamp(mtime, tz=timezone.utc)

    def has_date(self, date: datetime, *, check_tag: bool = False) -> bool:
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
    def short_notation(self) -> Self:
        path = cast("Path", self)
        if not path.is_absolute():
            untyped_path = Path("/") / path
            path = cast("Self", untyped_path)
        short_path = (
            path.relative_to(Path.HOME) if path.is_relative_to(Path.HOME) else path
        )
        return cast("Self", short_path)

    @classmethod
    @classproperty
    def source_root(cls) -> Self:
        return cls(__file__).parent.parent

    @classmethod
    @classproperty
    def assets(cls) -> Self:
        path = cls.script_assets / cls.source_root.name
        return cast("Self", path)

    @classmethod
    @classproperty
    def hashes(cls) -> Self:
        path = cls.assets / "hashes"
        return cast("Self", path)

    @classmethod
    @classproperty
    def backup_cache(cls) -> Self:
        path = cls.assets / "cache"
        return cast("Self", path)

    @classmethod
    @classproperty
    def config(cls) -> Self:
        path = cls.assets / "config"
        return cast("Self", path)

    @classmethod
    @classproperty
    def rclone_command_config(cls) -> Self:
        path = cls.config / "rclone_commands.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def ignore_names(cls) -> Self:
        path = cls.config / "ignore_names.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def ignore_patterns(cls) -> Self:
        path = cls.config / "ignore_patterns.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def profile_prefix(cls) -> str:
        return cast("str", cls.profile.yaml)

    @classmethod
    @classproperty
    def paths_include(cls) -> Self:
        path = cls.config / cls.profile_prefix / "include.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def paths_include_pull(cls) -> Self:
        path = cls.config / "pull_include.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def paths_exclude(cls) -> Self:
        path = cls.config / cls.profile_prefix / "exclude.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def profile_paths(cls) -> Self:
        path = cls.config / cls.profile_prefix / "profiles.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def number_of_paths(cls) -> Self:
        path = cls.assets / "volatile" / "number_of_paths"
        return cast("Self", path)

    @classmethod
    @classproperty
    def profiles(cls) -> Self:
        path = cls.assets / "profiles"
        return cast("Self", path)

    @classmethod
    @classproperty
    def profile(cls) -> Self:
        path = cls.config / "profile.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def active_profile(cls) -> Self:
        path = cls.profiles / "active.txt"
        return cast("Self", path)

    @classmethod
    @classproperty
    def resume(cls) -> Self:
        path = cls.docs / "Drive" / "resume" / "Resume"
        return cast("Self", path)

    @classmethod
    @classproperty
    def main_resume_pdf(cls) -> Self:
        path = cls.resume.parent / "Resume Quinten Roets.pdf"
        return cast("Self", path)

    @classmethod
    @classproperty
    def selected_resume_pdf(cls) -> Self:
        path = Path.resume / "Main" / Path.main_resume_pdf.name
        return cast("Self", path)

    @classmethod
    @classproperty
    def remote(cls) -> Self:
        return cls("backupmaster:")

    @classmethod
    @classproperty
    def rclone_config(cls) -> Self:
        path = cls.HOME / ".config" / "rclone" / "rclone.conf"
        return cast("Self", path)

    @classmethod
    @classproperty
    def backup_source(cls) -> Self:
        return cls("/")

    @classmethod
    @classproperty
    def canonicalized_home(cls) -> Self:
        return cls("home")

    @classmethod
    @classproperty
    def relative_home(cls) -> Self:
        path = cls.HOME.relative_to(cls("/"))
        return cast("Self", path)
