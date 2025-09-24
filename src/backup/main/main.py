import cli

from backup.backup import Backup
from backup.context import context
from backup.context.action import Action
from backup.models import Path
from backup.utils.parser import load_config


def main() -> None:
    """
    Backup important files across entire disk.
    """
    if context.options.configure:
        cli.open_urls(Path.backup_config)
    else:
        backup_files()


def backup_files() -> None:
    backup = Backup(load_config())
    action = (
        Action.pull if context.options.export_resume_changes else context.options.action
    )
    match action:
        case Action.status:
            backup.status()
        case Action.push:
            backup.push()
        case Action.pull:
            backup.pull()
