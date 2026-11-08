from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest

from backup.context import context
from backup.models import ChangeType, Path, PrintStructure
from backup.syncer import SyncConfig, Syncer
from backup.syncer.builder import create_syncer


@pytest.fixture
def mocked_syncer() -> Iterator[Syncer]:
    with Path.tempdir() as source, Path.tempdir() as dest:
        yield Syncer(SyncConfig(source=source, dest=dest))


@pytest.fixture
def mocked_syncer_with_filled_content(mocked_syncer: Syncer) -> Syncer:
    for number in (0, 1):
        (mocked_syncer.config.source / f"{number}.txt").text = "a"
    for number in (0, 2):
        (mocked_syncer.config.dest / f"{number}.txt").text = "aa"
    return mocked_syncer


def test_malformed_filters_indicated(mocked_syncer: Syncer) -> None:
    mocked_syncer.config.filter_rules = ["????"]
    with pytest.raises(ValueError, match="Invalid paths:"):
        mocked_syncer.capture_status()


def test_status(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    for directory in (syncer.config.source, syncer.config.dest):
        (directory / "3.txt").text = "a"
    status = syncer.capture_status(quiet=True)
    changes = {change.path: change.type for change in status}
    assert changes == {
        Path("0.txt"): ChangeType.modified,
        Path("1.txt"): ChangeType.created,
        Path("2.txt"): ChangeType.deleted,
    }


def test_push(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    source_hash = syncer.config.source.content_hash
    syncer.capture_push()
    assert syncer.config.dest.content_hash == source_hash


def test_pull(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    dest_hash = syncer.config.dest.content_hash
    syncer.capture_pull()
    assert syncer.config.source.content_hash == dest_hash


def test_push_skips_newer(mocked_syncer: Syncer) -> None:
    (mocked_syncer.config.source / "0.txt").touch(mtime=1)
    dest = mocked_syncer.config.dest / "0.txt"
    dest.text = "newer"
    with patch.object(context.config, "overwrite_newer", new=False):
        mocked_syncer.capture_push()
    assert dest.text == "newer"


def test_show_diff(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    (syncer.config.source / "0.txt").lines = ["same", "different"]
    (syncer.config.dest / "0.txt").lines = ["same", "different2"]
    changes = syncer.capture_status(quiet=True)
    PrintStructure.from_changes(changes).print(show_diff=True)


@pytest.fixture
def mocked_syncer_with_root_dest(
    mocked_syncer_with_filled_content: Syncer,
) -> Iterator[Syncer]:
    config = mocked_syncer_with_filled_content.config
    cli.run("rm -r", config.dest)
    cli.run("sudo mkdir", config.dest)
    yield mocked_syncer_with_filled_content
    cli.run("sudo rm -r", config.dest)


def test_push_to_root_dest(mocked_syncer_with_root_dest: Syncer) -> None:
    source_hash = mocked_syncer_with_root_dest.config.source.content_hash
    mocked_syncer_with_root_dest.push()
    assert mocked_syncer_with_root_dest.config.dest.content_hash == source_hash


def test_pull_to_root_source(mocked_syncer_with_root_dest: Syncer) -> None:
    config = mocked_syncer_with_root_dest.config
    source_hash = config.source.content_hash
    Syncer(SyncConfig(source=config.dest, dest=config.source)).pull()
    assert config.dest.content_hash == source_hash


def test_pull_with_specified_paths(mocked_syncer_with_filled_content: Syncer) -> None:
    config = mocked_syncer_with_filled_content.config
    Syncer(config.with_paths([Path("2.txt")])).pull()
    assert (config.source / "2.txt").exists()
    assert (config.source / "1.txt").exists()


def test_overlapping_sub_path() -> None:
    config = SyncConfig(source=Path("/a"), dest=Path("/a/sub_path/a"))
    assert config.overlapping_sub_path == Path("sub_path")


def test_create_syncer() -> None:
    create_syncer(path=Path("/"))


def test_export_files(mocked_syncer: Syncer) -> None:
    mocked_syncer.export_files("csv")
