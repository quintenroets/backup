from __future__ import annotations

import typing
from dataclasses import dataclass, field
from functools import cached_property

from backup.syncer import FileState

from .change import Action
from .path import Path, create_prefix

temporary_suffix = ".tmp"

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover


@dataclass
class SyncRecord:
    local: FileState = field(default_factory=FileState)
    remote: FileState = field(default_factory=FileState)

    def state(self, action: Action) -> FileState:
        """The side a transfer in this direction observes and compares against."""
        return self.local if action == Action.push else self.remote

    @property
    def values(self) -> list[float]:
        return [self.local.mtime, self.local.size, self.remote.mtime, self.remote.size]

    @classmethod
    def from_values(cls, values: list[typing.Any]) -> SyncRecord:
        local_mtime, local_size, remote_mtime, remote_size = values
        local = FileState(local_mtime, local_size)
        return cls(local, FileState(remote_mtime, remote_size))


@dataclass
class SyncState:
    path: Path

    @cached_property
    def records(self) -> dict[str, SyncRecord]:
        content = typing.cast(
            "dict[str, list[typing.Any]]",
            self.path.json if self.path.exists() else {},
        )
        return {key: SyncRecord.from_values(values) for key, values in content.items()}

    def save(self) -> None:
        temporary = Path(f"{self.path}{temporary_suffix}")
        temporary.json = {key: record.values for key, record in self.records.items()}
        temporary.replace(self.path)


@dataclass
class SyncRecords:
    """The records of one sync, addressed relative to the path it covers."""

    file: SyncState
    prefix: Path = field(default_factory=Path)

    def record(self, relative: str) -> SyncRecord | None:
        return self.file.records.get(self.key(relative))

    def update(self, relative: str, record: SyncRecord) -> None:
        self.file.records[self.key(relative)] = record

    def remove(self, relative: str) -> None:
        self.file.records.pop(self.key(relative), None)

    def relative_keys(self) -> Iterator[str]:
        if self.key_prefix:
            for key in self.file.records:
                if key.startswith(self.key_prefix):
                    yield key[len(self.key_prefix) :]
        else:
            yield from self.file.records

    def key(self, relative: str) -> str:
        return f"{self.key_prefix}{relative}"

    @cached_property
    def key_prefix(self) -> str:
        return create_prefix(self.prefix)
