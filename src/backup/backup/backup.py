from __future__ import annotations

import sys
from itertools import groupby
from typing import TYPE_CHECKING, Any

import cli

from backup.context import Action, context
from backup.models import BackupConfig, Change, Path, PrintStructure
from backup.syncer import SyncConfig, Syncer
from backup.utils.parser import parse_config

from .cache import CacheScanner, CacheSyncer, Entry

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    import superpathlib

Plan = tuple[BackupConfig, list[Change]]


def run(config: dict[str, Any]) -> list[Path]:
    root = Path.cwd() if context.options.sub_check else Path("/")
    backup_configs = list(parse_config(config, root))
    reverse = context.options.action == Action.pull
    if reverse and not context.options.cache_only:
        for backup_config in backup_configs:
            CacheSyncer(backup_config).sync_from_remote()
    plans = list(generate_plans(backup_configs, reverse=reverse))
    return list(apply(plans, reverse=reverse)) if any(confirm(plans)) else []


def generate_plans(configs: list[BackupConfig], *, reverse: bool) -> Iterator[Plan]:
    entries = cli.track_progress(
        generate_entries(configs),
        description="Checking",
        unit="Files",
        total=context.storage.number_of_paths,
        cleanup_after_finish=True,
    )
    changed = (entry for entry in entries if entry.is_changed())
    for config, group in groupby(changed, key=lambda entry: entry.config):
        paths = {entry.relative for entry in group}
        syncer = create_syncer(config, config.cache, paths)
        if changes := syncer.capture_status(reverse=reverse):
            yield config, changes


def generate_entries(configs: list[BackupConfig]) -> Iterator[Entry]:
    number_of_entries = 0
    for config in configs:
        for entry in CacheScanner(config).generate_entries():
            number_of_entries += 1
            yield entry
    context.storage.number_of_paths = number_of_entries


def apply(plans: list[Plan], *, reverse: bool) -> Iterator[Path]:
    for config, changes in plans:
        paths = [change.path for change in changes]
        create_syncer(config, config.dest, paths).push(reverse=reverse)
        create_syncer(config, config.cache, paths).push()
        yield from (config.source / path for path in paths)


def confirm(plans: list[Plan]) -> Iterator[bool]:
    if plans and context.options.confirm_push and sys.stdin.isatty():
        cli.console.rule("Backup")
        for show_diff in (False, True):
            for _, changes in plans:
                PrintStructure.from_changes(changes).print(show_diff=show_diff)
            yield cli.confirm(f"{context.options.action.capitalize()}?", default=True)
    else:
        yield True


def create_syncer(
    config: BackupConfig,
    dest: Path,
    paths: Iterable[superpathlib.Path],
) -> Syncer:
    return Syncer(SyncConfig(source=config.source, dest=dest, paths=list(paths)))
