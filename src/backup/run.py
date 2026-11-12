from __future__ import annotations

import sys
from itertools import chain, groupby
from typing import TYPE_CHECKING, Any

import cli

from .cache import CacheScanner, CacheSyncer
from .context import Action, context
from .parser import parse_config
from .path import Path
from .syncer import SyncConfig, Syncer

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    import superpathlib

    from .models import BackupConfig, Plan


def run(config: dict[str, Any]) -> list[Path]:
    root = Path.cwd() if context.options.sub_check else Path("/")
    backup_configs = list(parse_config(config, root))
    reverse = context.options.action == Action.pull
    if reverse and not context.options.cache_only:
        for backup_config in backup_configs:
            CacheSyncer(backup_config).sync_from_remote()
    plans = list(generate_plans(backup_configs, reverse=reverse))
    confirmed = any(confirm(plans, reverse=reverse))
    return list(apply(plans, reverse=reverse)) if confirmed else []


def generate_plans(configs: list[BackupConfig], *, reverse: bool) -> Iterator[Plan]:
    scans = (CacheScanner(config).generate_entries() for config in configs)
    entries = cli.track_progress(
        chain.from_iterable(scans),
        description="Checking",
        unit="Files",
        cleanup_after_finish=True,
    )
    changed = (entry for entry in entries if entry.is_changed())
    for config, group in groupby(changed, key=lambda entry: entry.config):
        paths = {entry.relative for entry in group}
        syncer = create_syncer(config, config.cache, paths)
        if changes := syncer.capture_status(reverse=reverse):
            yield config, changes


def apply(plans: list[Plan], *, reverse: bool) -> Iterator[Path]:
    for config, changes in plans:
        paths = [change.path for change in changes]
        create_syncer(config, config.dest, paths).push(reverse=reverse)
        create_syncer(config, config.cache, paths).push()
        yield from (config.source / path for path in paths)


def confirm(plans: list[Plan], *, reverse: bool) -> Iterator[bool]:
    if plans and context.options.confirm_push and sys.stdin.isatty():
        from .display import print_changes  # noqa: PLC0415

        cli.console.rule("Backup")
        for show_diff in (False, True):
            for plan in plans:
                print_changes(plan, show_diff=show_diff, reverse=reverse)
            yield cli.confirm(f"{context.options.action.capitalize()}?", default=True)
    else:
        yield True


def create_syncer(
    config: BackupConfig,
    dest: Path,
    paths: Iterable[superpathlib.Path],
) -> Syncer:
    return Syncer(SyncConfig(config.source, dest).with_paths(paths))
