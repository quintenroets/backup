import os
from collections.abc import Iterator
from typing import Any, cast

import pytest

from backup.backups.cache.cache import Backup
from backup.backups.cache.detailed_entry import Entry
from backup.context import Context
from backup.models import Path

is_running_in_ci = "GITHUB_ACTIONS" in os.environ


test_with_tags = pytest.mark.skipif(
    is_running_in_ci,
    reason="XDG Tags are not supported in CI",
)


@pytest.fixture
def file() -> Iterator[Path]:  # pragma: nocover
    with Path.tempfile() as path:
        yield path


@pytest.fixture
def entry(file: Path) -> Entry:  # pragma: nocover
    dummy_path = Path()
    return Entry(source_root=file.parent, dest_root=dummy_path, source=file)


def test_cache() -> None:
    includes = [{"chromium": ["b"]}]
    typed_includes = cast("list[str | dict[str, Any]]", includes)
    Backup.remove_browser(includes=typed_includes)


def test_overlapping_source(test_context: Context) -> None:
    source = test_context.config.cache_path / "sub_path"
    Backup(source=source).status()


@test_with_tags
def test_exported_tag_excluded(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "exported"
    assert entry.exclude()


@test_with_tags
def test_other_tags_included(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "anything"
    assert not entry.exclude()
