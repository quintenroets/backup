from __future__ import annotations

import sys
from itertools import chain, groupby
from typing import TYPE_CHECKING, Any

import cli
from superpathlib import Path

from .cache import CacheScanner
from .context import Action, context
from .parser import parse_config
from .syncer import Syncer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .models import Backup, Plan


def run(config: dict[str, Any]) -> list[Path]:
    root = Path.cwd() if context.options.sub_check else Path("/")
    backups = list(parse_config(config, root))
    reverse = context.options.action == Action.pull
    if reverse and not context.options.cache_only:
        for backup in backups:
            sync_cache(backup)
    plans = list(generate_plans(backups, reverse=reverse))
    confirmed = any(confirm(plans, reverse=reverse))
    return list(apply(plans, reverse=reverse)) if confirmed else []


def sync_cache(backup: Backup) -> None:
    backup.cache.mkdir(parents=True, exist_ok=True)
    location = str(backup.dest).split(":")[-1]
    with cli.console.status(f"Reading remote filesystem at {location}"):
        cache, remote = Syncer(backup.cache, backup.dest, backup.rules).list_mtimes()
    for path in cache.keys() - remote:
        (backup.cache / path).unlink()
    for path, mtime in remote.items() - cache.items():
        cache_path = backup.cache / path
        source_path = backup.source / path
        if int(source_path.mtime) == int(mtime):
            source_path.copy_to(cache_path)
        else:
            # trigger update
            cache_path.text = "" if source_path.size else " "


def generate_plans(backups: list[Backup], *, reverse: bool) -> Iterator[Plan]:
    scans = (CacheScanner(backup).generate_entries() for backup in backups)
    entries = cli.track_progress(chain.from_iterable(scans), "Checking", "Files")
    changed = (entry for entry in entries if entry.is_changed())
    for backup, group in groupby(changed, key=lambda entry: entry.backup):
        paths = {entry.relative for entry in group}
        syncer = Syncer(backup.source, backup.cache).with_paths(paths)
        if changes := syncer.capture_status(reverse=reverse):
            yield backup, changes


def apply(plans: list[Plan], *, reverse: bool) -> Iterator[Path]:
    for backup, changes in plans:
        paths = [change.path for change in changes]
        syncer = Syncer(backup.source, backup.dest).with_paths(paths)
        (syncer.reversed if reverse else syncer).sync()
        Syncer(backup.source, backup.cache).with_paths(paths).sync()
        yield from (backup.source / path for path in paths)


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
