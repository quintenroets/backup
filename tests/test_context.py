import sys
from unittest.mock import patch

from package_utils.cli.entry_point import invoke_from_cli_args

from backup.context import Options, context
from backup.models import Path
from backup.run import run
from tests.conftest import BackupSetup


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


def test_entry_point_backs_up_what_its_config_path_names(backup: BackupSetup) -> None:
    """The console script: the config file is the only thing the CLI is handed."""
    (backup.source / "file.txt").text = "content"
    with Path.tempfile() as config_path:
        config_path.yaml = backup.config
        options = Options(confirm=False, config_path=config_path)
        with patch.dict(context.__dict__, options=options):
            plans = run()
    paths = [path for plan in plans for path in plan.absolute_paths]
    assert paths == [backup.source / "file.txt"]
