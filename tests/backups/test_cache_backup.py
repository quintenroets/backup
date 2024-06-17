from typing import Any, cast

from backup.backups.cache.cache import Backup
from backup.context import Context


def test_cache() -> None:
    includes = [{"chromium": ["b"]}]
    typed_includes = cast(list[str | dict[str, Any]], includes)
    Backup.remove_browser(includes=typed_includes)


def test_overlapping_source(test_context: Context) -> None:
    source = test_context.config.cache_path / "sub_path"
    Backup(source=source).status()
