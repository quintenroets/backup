import json
from collections.abc import Iterator
from unittest.mock import patch

import cli
import pytest

from backup.context import context
from backup.models import Change, ChangeTypes, Path
from backup.syncer import SyncConfig, Syncer


def test_malformed_filters_indicated(mocked_syncer: Syncer) -> None:
    mocked_syncer.config.filter_rules = ["????"]
    with pytest.raises(ValueError, match="Invalid paths:"):
        mocked_syncer.capture_status()


def test_setup_trigger() -> None:
    with patch("backup.utils.setup.check_setup") as mocked_setup:
        Syncer()
        mocked_setup.assert_called_once()


def test_syncer_command() -> None:
    Syncer().run("version")


def test_status(mocked_syncer_with_filled_content: Syncer) -> None:
    expected_changes = {
        Change(Path("0.txt"), ChangeTypes.modified),
        Change(Path("1.txt"), ChangeTypes.created),
        Change(Path("2.txt"), ChangeTypes.deleted),
    }
    assert capture_changes(mocked_syncer_with_filled_content) == expected_changes


def capture_changes(syncer: Syncer) -> set[Change]:
    status = syncer.capture_status(quiet=True, is_cache=True)
    return {Change(change.path, change.type) for change in status}


def test_push(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    hash_value = syncer.config.source.content_hash
    syncer.capture_push()
    syncer.push()
    assert_no_differences(syncer)
    assert syncer.config.source.content_hash == hash_value


def test_pull(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    hash_value = syncer.config.dest.content_hash
    syncer.capture_pull()
    syncer.pull()
    assert_no_differences(syncer)
    assert syncer.config.dest.content_hash == hash_value


def test_ls(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    path = next(path for path in syncer.config.source.iterdir() if path.is_file())
    file_info = syncer.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


def test_single_file_copy(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    path = next(syncer.config.source.iterdir())
    dest = syncer.config.dest / path.relative_to(syncer.config.source)
    syncer.capture_output("copyto", path, dest)


def test_all_options(mocked_syncer_with_filled_content: Syncer) -> None:
    overwrite_newer = context.config.overwrite_newer
    context.config.overwrite_newer = False
    mocked_syncer_with_filled_content.capture_push()
    context.config.overwrite_newer = overwrite_newer


@pytest.mark.parametrize("color", [True, False])
def test_show_diff(mocked_syncer_with_filled_content: Syncer, *, color: bool) -> None:
    syncer = mocked_syncer_with_filled_content
    (syncer.config.source / "0.txt").lines = ["same", "different"]
    (syncer.config.dest / "0.txt").lines = ["same", "different2"]
    context.options.show_file_diffs = True
    changes = syncer.capture_status(quiet=True, is_cache=True)
    changes.ask_confirm(message="message", show_diff=True)
    change = changes.changes[0]
    change.print()
    change.get_diff_lines(color=color)
    context.options.show_file_diffs = False


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
    assert not mocked_syncer_with_root_dest.capture_status().paths
    assert mocked_syncer_with_root_dest.config.source.content_hash == source_hash


def test_pull_to_root_source(mocked_syncer_with_root_dest: Syncer) -> None:
    config = SyncConfig(
        source=mocked_syncer_with_root_dest.config.dest,
        dest=mocked_syncer_with_root_dest.config.source,
    )
    syncer = Syncer(config)
    dest_hash = syncer.config.dest.content_hash
    syncer.pull()
    assert_no_differences(syncer)
    assert syncer.config.dest.content_hash == dest_hash


def test_pull_with_specified_paths(
    mocked_syncer_with_filled_content: Syncer,
) -> None:
    paths = mocked_syncer_with_filled_content.capture_status(
        quiet=True,
        is_cache=True,
    ).paths
    syncer = Syncer(mocked_syncer_with_filled_content.config.with_paths(paths))
    dest_hash = syncer.config.dest.content_hash
    syncer.pull()
    assert_no_differences(mocked_syncer_with_filled_content)
    assert syncer.config.dest.content_hash == dest_hash


def test_overlapping_sub_path(mocked_syncer: Syncer) -> None:
    source = mocked_syncer.config.source
    config = SyncConfig(
        source=mocked_syncer.config.source,
        dest=source / "sub_path" / source.name,
    )
    assert config.overlapping_sub_path is not None


def assert_no_differences(syncer: Syncer) -> None:
    assert not syncer.capture_status(quiet=True, is_cache=True).paths
