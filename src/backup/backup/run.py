import sys
from collections.abc import Iterator
from contextlib import contextmanager
from functools import cache
from typing import Any, cast

import cli
import superpathlib
from package_utils.context.entry_point import create_entry_point

from backup.syncer import RcloneConfig, SyncConfig, Syncer, load_rclone_env

from .change_tree import ChangeTree, DiffRoots
from .context import Options, context
from .models import Action, Changes, Config, Path, SyncState
from .parser import parse_config
from .scanners import scan_remotes, scan_sources
from .transfer_plan import TransferPlan


def back_up() -> list[Changes]:
    """
    Back up important files across the entire disk.
    """
    return run_config(context.config, context.options)


def run(config: dict[str, Any], options: Options | None = None) -> list[Changes]:
    """Back up according to a config, with one run driven by the given options."""
    return run_config(Config.from_dict(config), options)


def run_config(
    serialized_config: Config,
    options: Options | None = None,
) -> list[Changes]:
    resolved = Options() if options is None else options
    sync_state = SyncState(Path(serialized_config.sync_state))
    sub_check_path = Path.cwd() if resolved.sub_check else None
    backup_configs = list(parse_config(serialized_config, sync_state, sub_check_path))
    plans = (
        scan_remotes(backup_configs)
        if resolved.action == Action.pull
        else scan_sources(backup_configs, len(sync_state.records))
    )
    return apply_confirmed(plans, sync_state, resolved)


def create_syncer(
    *,
    path: superpathlib.Path | None = None,
    directory: superpathlib.Path | None = None,
    remote: str | None = None,
    rclone: RcloneConfig | None = None,
) -> Syncer:
    target = cast("superpathlib.Path", directory if directory is not None else path)
    is_home = target.is_relative_to(Path.HOME)
    source = Path.HOME if is_home else Path.backup_source
    remote_root = Path(resolve_remote(remote))
    dest = remote_root / "home" if is_home else remote_root
    config = SyncConfig(source=source, dest=dest, path=path, directory=directory)
    return Syncer(config, RcloneConfig() if rclone is None else rclone)


@cache
def resolve_remote(remote: str | None = None) -> str:
    return (
        remote
        if remote is not None
        else cli.capture_output_lines("rclone listremotes", env=load_rclone_env())[0]
    )


def apply_confirmed(
    plans: list[TransferPlan],
    sync_state: SyncState,
    options: Options,
) -> list[Changes]:
    changed = [plan for plan in plans if plan.changes]
    confirmed = confirm_changes(changed, options)
    if confirmed:
        for plan in changed:
            plan.apply()
        sync_state.save()
    return [plan.changes for plan in plans] if confirmed else []


def confirm_changes(changed: list[TransferPlan], options: Options) -> bool:
    is_interactive = options.confirm and sys.stdin.isatty()
    needs_confirmation = bool(changed) and is_interactive
    if changed and (needs_confirmation or options.diff):
        show_changes(changed, diff=options.diff)
    message = f"{options.action.capitalize()}?"
    return cli.confirm(message, default=True) if needs_confirmation else True


def show_changes(plans: list[TransferPlan], *, diff: bool) -> None:
    cli.console.rule("Backup")
    for plan in plans:
        with create_diff_roots(plan, diff=diff) as diff_roots:
            ChangeTree.from_changes(plan.changes).print(diff_roots)


@contextmanager
def create_diff_roots(plan: TransferPlan, *, diff: bool) -> Iterator[DiffRoots | None]:
    if diff:
        with Path.tempdir() as staging:
            fetch_remote_content(plan, staging)
            yield DiffRoots(plan.backup_config.source, staging)
    else:
        yield None


def fetch_remote_content(plan: TransferPlan, staging: Path) -> None:
    if plan.changes.paths:
        dest = plan.backup_config.dest
        config = SyncConfig(source=staging, dest=dest, paths=plan.changes.paths)
        with cli.status("Comparing with remote content"):
            plan.backup_config.create_syncer(config).copy_from_remote()


entry_point = create_entry_point(back_up, context)
