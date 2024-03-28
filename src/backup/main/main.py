import cli

from ..backups import Backup
from ..context import context
from ..models import Action, Path


def main() -> None:
    """
    Backup important files across entire disk.
    """
    if context.options.configure:
        cli.urlopen(Path.config)
    else:
        backup_files()


def backup_files() -> None:
    backup = Backup()
    action = Action.pull if context.options.export_resume else context.options.action
    backup.run_action(action)
