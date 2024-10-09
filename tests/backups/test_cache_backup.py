from collections.abc import Iterator
from typing import Any, cast

import pytest

from backup.backups.cache.cache import Backup
from backup.backups.cache.detailed_entry import Entry
from backup.context import Context
from backup.models import Path


@pytest.fixture
def file() -> Iterator[Path]:
    with Path.tempfile() as path:
        yield path


@pytest.fixture
def entry(file: Path) -> Entry:
    dummy_path = Path()
    return Entry(source_root=file.parent, dest_root=dummy_path, source=file)


def test_cache() -> None:
    includes = [{"chromium": ["b"]}]
    typed_includes = cast(list[str | dict[str, Any]], includes)
    Backup.remove_browser(includes=typed_includes)


def test_overlapping_source(test_context: Context) -> None:
    source = test_context.config.cache_path / "sub_path"
    Backup(source=source).status()


def test_exported_tag_excluded(entry: Entry) -> None:
    entry.source.tag = "exported"
    assert entry.exclude()


def test_other_tags_included(entry: Entry) -> None:
    entry.source.tag = "anything"
    assert not entry.exclude()
