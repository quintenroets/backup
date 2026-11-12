from typing import Self, cast

import superpathlib
from simple_classproperty import classproperty


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

    @classmethod
    @classproperty
    def assets(cls) -> Self:
        return cast("Self", cls.script_assets / "backup")

    @classmethod
    @classproperty
    def backup_source(cls) -> Self:
        return cls("/")
