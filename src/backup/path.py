from typing import Self, cast

import superpathlib
from simple_classproperty import classproperty


class Path(superpathlib.Path):
    @classmethod
    @classproperty
    def assets(cls) -> Self:
        return cast("Self", cls.script_assets / "backup")

    @classmethod
    @classproperty
    def backup_source(cls) -> Self:
        return cls("/")
