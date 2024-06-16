from typing import Any, cast

from backup.backups.cache.cache import Backup


def test_cache() -> None:
    includes = [{"chromium": ["b"]}]
    typed_includes = cast(list[str | dict[str, Any]], includes)
    Backup.remove_browser(includes=typed_includes)
