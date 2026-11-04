import time
import typing
from dataclasses import dataclass
from typing import Any, ClassVar, Generic, TypeVar

from package_utils.storage import cached_file_content
from superpathlib import Path

T = TypeVar("T")


@dataclass
class CachedFileContent(cached_file_content.CachedFileContent[T], Generic[T]):
    _storage: ClassVar[dict[Path, Any]] = {}

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> T:
        untyped_result = CachedFileContent._storage.get(self.path, self.default)
        return typing.cast("T", untyped_result)

    def __set__(self, instance: Any, value: T) -> None:
        CachedFileContent._storage[self.path] = value
        self.mtime = time.time()
