from __future__ import annotations

import json
import sys
from datetime import datetime
from itertools import chain, groupby
from typing import TYPE_CHECKING, Any

import cli

from .cache import CacheScanner
from .context import Action, context
from .parser import parse_config
from .path import Path
from .syncer import SyncConfig, Syncer

if TYPE_CHECKING:
    from collections.abc import Iterable, Iterator

    import superpathlib

    from .models import BackupConfig, PathRule, Plan


def run(config: dict[str, Any]) -> list[Path]:
    root = Path.cwd() if context.options.sub_check else Path("/")
    backup_configs = list(parse_config(config, root))
    reverse = context.options.action == Action.pull
    if reverse and not context.options.cache_only:
        for backup_config in backup_configs:
            sync_cache(backup_config)
    plans = list(generate_plans(backup_configs, reverse=reverse))
    confirmed = any(confirm(plans, reverse=reverse))
    return list(apply(plans, reverse=reverse)) if confirmed else []


def sync_cache(backup: BackupConfig) -> None:
    with cli.status(f"Reading remote filesystem at {str(backup.dest).split(':')[-1]}"):
        remote_mtimes = list_mtimes(backup.dest, backup.rules)
    backup.cache.mkdir(parents=True, exist_ok=True)
    cache_mtimes = list_mtimes(backup.cache, backup.rules)
    for path in cache_mtimes.keys() - remote_mtimes:
        (backup.cache / path).unlink()
    for path, mtime in remote_mtimes.items() - cache_mtimes.items():
        cache_path = backup.cache / path
        source_path = backup.source / path
        if int(source_path.mtime) == mtime:
            source_path.copy_to(cache_path)
        else:
            # trigger update
            cache_path.text = "" if source_path.size else " "


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
        syncer = create_syncer(config, config.dest, paths)
        (Syncer(syncer.config.reversed) if reverse else syncer).push()
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


def list_mtimes(directory: Path, rules: list[PathRule]) -> dict[Path, int]:
    syncer = Syncer(SyncConfig(directory, directory, rules))
    args = "lsjson", "-R", "--files-only", "--no-mimetype", directory
    return {
        Path(row["Path"]): int(datetime.fromisoformat(row["ModTime"]).timestamp())
        for row in json.loads(syncer.capture_output(*args))
    }
