from __future__ import annotations

from typing import TYPE_CHECKING, Self, cast

import superpathlib
from simple_classproperty import classproperty

if TYPE_CHECKING:
    from datetime import datetime


class Path(superpathlib.Path):
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

    def extract_date(self) -> datetime:
        from datetime import UTC, datetime  # noqa: PLC0415

        return datetime.fromtimestamp(self.mtime, tz=UTC)

    def has_date(self, date: datetime) -> bool:
        path_date = self.extract_date()
        return self.extract_date_tuple(date) == self.extract_date_tuple(path_date)

    @classmethod
    def extract_date_tuple(cls, date: datetime) -> tuple[int, ...]:
        # drive remote only minute precision and month range
        return date.month, date.day, date.hour, date.minute

    @classmethod
    @classproperty
    def assets(cls) -> Self:
        return cast("Self", cls.script_assets / "backup")

    @classmethod
    @classproperty
    def backup_source(cls) -> Self:
        return cls("/")
