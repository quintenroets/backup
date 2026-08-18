from unittest.mock import patch

from package_utils.cli import instantiate_from_cli_args
from package_utils.cli.entry_point import defaults_cover_arguments

from backup.backup.context import Options, context
from backup.backup.models import Path
from backup.backup.run import back_up


def test_bare_invocation_needs_no_parser() -> None:
    """The hot path: building one imports typer, which costs as much as the run."""
    with patch("sys.argv", ["backup"]):
        assert defaults_cover_arguments(Options)


def test_an_argument_still_reaches_the_parser() -> None:
    with patch("sys.argv", ["backup", "push"]):
        assert not defaults_cover_arguments(Options)


def test_an_argument_reaches_the_options() -> None:
    """Parsing has to resolve annotations naming a typer this module never imports."""
    with patch("sys.argv", ["backup", "--diff"]):
        options = instantiate_from_cli_args(Options)
    assert options.diff


def test_entry_point_backs_up_what_its_config_path_names() -> None:
    """The console script: the config file is the only thing the CLI is handed."""
    with Path.tempdir() as directory, Path.tempdir() as dest:
        source = directory / "source"
        (source / "file.txt").text = "content"
        config_path = directory / "backup.yaml"
        config_path.yaml = {
            "source": str(source),
            "dest": str(dest),
            "sync_state": str(directory / "sync-state.json"),
            "syncs": [{"includes": [""]}],
        }
        context.options = Options(confirm=False, config_path=config_path)
        context.loaders.config.value = None
        try:
            changes = back_up()
        finally:
            context.options = Options()
            context.loaders.config.value = None
    assert [str(change.path) for one in changes for change in one] == ["file.txt"]
