import sys
from unittest.mock import patch

from package_utils.cli.entry_point import invoke_from_cli_args

from backup.backup.context import Options, context
from backup.backup.models import Path
from backup.backup.run import run


def test_bare_invocation_needs_no_parser() -> None:
    """The hot path: building one imports typer, which costs as much as the run."""
    with patch.dict(sys.modules), patch("sys.argv", ["backup"]):
        for module in ("typer", "package_utils.cli.parser"):
            sys.modules.pop(module, None)
        invoke_from_cli_args(Options)
        assert "typer" not in sys.modules


def test_an_argument_reaches_the_options() -> None:
    """Parsing has to resolve annotations naming a typer this module never imports."""
    with patch("sys.argv", ["backup", "--diff"]):
        options = invoke_from_cli_args(Options)
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
        context.__dict__.pop("config", None)
        try:
            changes = run()
        finally:
            context.options = Options()
            context.__dict__.pop("config", None)
    assert [str(change.path) for one in changes for change in one] == ["file.txt"]
