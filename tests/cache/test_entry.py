import os
from backup.backup.config import BackupConfig
from collections.abc import Iterator

import pytest

from backup.backup.cache.entry import Entry
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
    config = BackupConfig(source=file.parent, dest=dummy_path, cache=dummy_path)
    return Entry(config, source=file)


@test_with_tags
def test_exported_tag_excluded(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "exported"
    assert entry.exclude()


@test_with_tags
def test_other_tags_included(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "anything"
    assert not entry.exclude()
