from __future__ import annotations

import sys
from functools import partial
from itertools import groupby
from typing import TYPE_CHECKING

import cli
from superpathlib import Path

from .context import Action, context
from .parser import parse_config
from .syncer import Syncer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from .models import Backup, Config, Plan


def run(config: Config) -> list[Path]:
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
    scans = (entry for backup in backups for entry in scan_cache(backup))
    entries = cli.track_progress(scans, "Checking", "Files")
    changed = (entry for entry in entries if is_changed(*entry))
    for backup, group in groupby(changed, key=lambda entry: entry[0]):
        paths = {path for *_, path in group}
        syncer = Syncer(backup.source, backup.cache).with_paths(paths)
        if changes := syncer.capture_status(reverse=reverse):
            yield backup, changes


def scan_cache(backup: Backup) -> Iterator[tuple[Backup, Path, Path]]:
    visited: set[Path] = set()
    exclude_source = partial(is_excluded, backup, visited)
    sides = (backup.source, exclude_source), (backup.cache, visited.__contains__)
    for rule in backup.rules:
        if rule.include:
            for root, exclude in sides:
                for path in (root / rule.path).find(Path.is_file, exclude=exclude):
                    yield backup, root, path.relative_to(root)
        visited.update(root / rule.path for root, _ in sides)


def is_excluded(backup: Backup, visited: set[Path], path: Path) -> bool:
    return path in visited or (path / ".git").exists() or backup.ignores.matches(path)


def is_changed(backup: Backup, root: Path, path: Path) -> bool:
    changed = (backup.source / path).mtime != (backup.cache / path).mtime
    max_size = context.config.max_backup_size
    return changed and ((root / path).size <= max_size or path.suffix == ".zip")


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
