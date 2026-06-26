import os
from collections.abc import Iterator

import pytest

from backup.backup import Backup
from backup.backup.cache.entry import Entry, extract_hash_path
from backup.models import BackupConfig, Path

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
@pytest.mark.usefixtures("mocked_backup")
def test_other_tags_included(entry: Entry) -> None:  # pragma: nocover
    entry.source.tag = "anything"
    assert not entry.exclude()


def test_hash_path_not_set_when_hashes_outside_source(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    with Path.tempdir() as source:
        sub_config = BackupConfig(source=source, dest=config.dest, cache=config.cache)
        path = source / "file.txt"
        path.touch()
        entry = Entry(config=sub_config, source=path)
        entry.assign_hash_path()
        assert entry.hash_path is None


def test_get_paths_includes_existing_hash_path(mocked_backup: Backup) -> None:
    config = mocked_backup.backup_configs[0]
    path = config.source / "file.txt"
    path.touch()
    entry = Entry(config=config, source=path)
    extract_hash_path(path, config).text = "hash"
    entry.assign_hash_path()
    assert entry.hash_path is not None
    assert list(entry.get_paths()) == [entry.relative, entry.hash_path]
