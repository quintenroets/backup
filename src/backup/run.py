import sys

import cli
from package_utils.context.entry_point import create_entry_point

from .change_tree import show_changes
from .context import Options, context
from .models import Action, Config, Path, load_sync_state, save_sync_state
from .parser import parse_config
from .scanners import scan_remote, scan_sources
from .transfer_plan import TransferPlan


def run() -> list[TransferPlan]:
    """Back up important files across the entire disk."""
    return run_config(context.config, context.options)


def run_config(config: Config, options: Options) -> list[TransferPlan]:
    path = Path(config.sync_state)
    sync_state = load_sync_state(path)
    sub_check_path = Path.cwd() if options.sub_check else None
    backup_configs = list(parse_config(config, sync_state, sub_check_path))
    plans = (
        [scan_remote(backup_config) for backup_config in backup_configs]
        if options.action == Action.pull
        else scan_sources(backup_configs)
    )
    changed = [plan for plan in plans if plan.changes]
    applied = changed if changed and confirm_changes(changed, options) else []
    for plan in applied:
        plan.apply(options.action)
    save_sync_state(path, sync_state)
    return applied


def confirm_changes(changed: list[TransferPlan], options: Options) -> bool:
    is_interactive = options.confirm and sys.stdin.isatty()
    if is_interactive or options.diff:
        show_changes(changed, options)
    message = f"{options.action.capitalize()}?"
    return not is_interactive or cli.confirm(message, default=True)


entry_point = create_entry_point(run, context)
