from collections.abc import Iterator

import cli
import pytest

from backup import create_syncer
from backup.backup.models import Path
from backup.backup.run import resolve_remote
from backup.syncer import RcloneConfig, SyncConfig, Syncer
from backup.syncer.cli_runner import CliRunner
from backup.syncer.syncer import parse_modified_time

dummy_config = SyncConfig(source=Path("/"), dest=Path("dest:"))


def test_syncer_command() -> None:
    assert Syncer(dummy_config).run("version").returncode == 0


def test_list_remote_files(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    files = syncer.list_remote_files()
    expected_file = syncer.config.dest / "0.txt"
    assert files["0.txt"].size == expected_file.size
    assert files["0.txt"].mtime == pytest.approx(expected_file.mtime)


@pytest.mark.parametrize(
    "value",
    ["2023-01-01T12:00:00.123456789Z", "2023-01-01T12:00:00+01:00"],
)
def test_parse_modified_time(value: str) -> None:
    assert parse_modified_time(value) > 0


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


def test_preserved_newer_files_add_the_update_option() -> None:
    """--update is what stops a push from overwriting a newer remote file."""
    options = RcloneConfig(overwrite_newer=False)
    assert "--update" in CliRunner(dummy_config, options).generate_options()


def test_overwritten_newer_files_omit_the_update_option() -> None:
    options = RcloneConfig(overwrite_newer=True)
    assert "--update" not in CliRunner(dummy_config, options).generate_options()


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
    assert_no_differences(mocked_syncer_with_root_dest)
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
    paths = [Path("0.txt"), Path("2.txt")]
    syncer = Syncer(mocked_syncer_with_filled_content.config.with_paths(paths))
    dest_hash = syncer.config.dest.content_hash
    syncer.pull()
    assert syncer.config.dest.content_hash == dest_hash
    for path in paths:
        source_file = syncer.config.source / path
        assert source_file.text == (syncer.config.dest / path).text


def assert_no_differences(syncer: Syncer) -> None:
    syncer.cli_runner(action="check").capture_output()


def test_create_syncer_scopes_a_home_path_to_the_home_remote() -> None:
    syncer = create_syncer(path=Path.HOME / "file.txt")
    assert syncer.config.source == Path.HOME
    assert syncer.config.dest == Path(resolve_remote()) / "home"


def test_create_syncer_scopes_an_outside_directory_to_the_bare_remote(
    mocked_syncer: Syncer,
) -> None:
    directory = mocked_syncer.config.source
    syncer = create_syncer(directory=directory)
    assert syncer.config.source == Path.backup_source
    assert syncer.config.dest == Path(resolve_remote())
    assert syncer.config.directory == directory


def test_export_files(mocked_syncer_with_filled_content: Syncer) -> None:
    syncer = mocked_syncer_with_filled_content
    syncer.export_files("csv")
    remote_only_file = syncer.config.source / "2.txt"
    assert remote_only_file.text == (syncer.config.dest / "2.txt").text
