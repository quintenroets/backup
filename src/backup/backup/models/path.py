from __future__ import annotations

import os
import typing
from itertools import chain
from typing import Self, cast

import superpathlib
from simple_classproperty import classproperty

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover


def create_prefix(path: Path) -> str:
    prefix = str(path)
    return "" if prefix in ("", ".") else f"{prefix}/"


def generate_ancestors(relative: str) -> Iterator[str]:
    yield relative
    while "/" in relative:
        relative = relative.rsplit("/", 1)[0]
        yield relative


def resolve_overlapping_sub_path(
    source: superpathlib.Path,
    dest: superpathlib.Path,
) -> superpathlib.Path | None:
    """The sub path at which either root contains the other, in both directions."""
    overlaps = chain(
        generate_overlapping_sub_path(source, dest),
        generate_overlapping_sub_path(dest, source),
    )
    return next(overlaps, None)


def generate_overlapping_sub_path(
    source: superpathlib.Path,
    dest: superpathlib.Path,
) -> Iterator[superpathlib.Path]:
    if source.is_relative_to(dest):
        path = source.relative_to(dest)
        while path.name == dest.name:
            path = path.parent
            dest = dest.parent
        yield path


class Path(superpathlib.Path):
    @property
    def is_root(self) -> bool:
        is_remote = self.parts[0].endswith(":")
        return not is_remote and not self.user_has_write_access()

    def user_has_write_access(self) -> bool:
        path = self
        while not path.exists():
            path = path.parent
        return os.access(path, os.W_OK)

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
    def sync_state(cls) -> Self:
        path = cls.assets / "sync-state.json"
        return cast("Self", path)

    @classmethod
    @classproperty
    def config(cls) -> Self:
        path = cls.assets / "backup.yaml"
        return cast("Self", path)

    @classmethod
    @classproperty
    def backup_source(cls) -> Self:
        return cls("/")
