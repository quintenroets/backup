import os
from collections.abc import Iterator

import pytest

from backup.backup.cache.detailed_entry import Entry
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


@test_with_tags
def test_exported_tag_excluded(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "exported"
    assert entry.exclude()


@test_with_tags
def test_other_tags_included(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "anything"
    assert not entry.exclude()
