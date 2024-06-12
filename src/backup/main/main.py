import cli

from ..backups import Backup
from ..context import context
from ..models import Action, Path


def main() -> None:
    """
    Backup important files across entire disk.
    """
    if context.options.configure:
        cli.open_urls(Path.config)
    else:
        backup_files()


def backup_files() -> None:
    backup = Backup()
    action = (
        Action.pull if context.options.export_resume_changes else context.options.action
    )
    backup.run_action(action)
