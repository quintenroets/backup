from __future__ import annotations

import typing
from operator import attrgetter

from .models import BackupConfig, Config, Entries, Path, Scope, SyncRecords, SyncState
from .syncer import PathRule

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover

version_placeholder = "__VERSION__"


def parse_config(
    config: Config,
    sync_state: SyncState,
    sub_check_path: Path | None,
) -> Iterator[BackupConfig]:
    root_dest = Path(config.source if config.dest == "/" else config.dest)
    for entry in config.syncs:
        joined = Path(config.source) / entry.source
        source = Path.HOME if joined == Path("/HOME") else joined
        sub_path = resolve_sub_path(source, sub_check_path)
        if sub_path is not None and source.exists():
            dest = root_dest / entry.dest
            parsed = parse_rules(source, entry.includes, entry.excludes)
            owned = generate_owned_exclusions(source, dest, Path(config.sync_state))
            rules = [*owned, *generate_scoped_rules(parsed, sub_path)]
            if any(rule.include for rule in rules):
                records = sync_state.setdefault(entry.dest, SyncRecords())
                scope = Scope(rules, config.ignores, config.max_backup_size)
                yield BackupConfig(source, dest, records, scope, config.rclone)


def generate_owned_exclusions(
    source: Path,
    dest: Path,
    sync_state_path: Path,
) -> Iterator[PathRule]:
    for inner, container in ((source, dest), (dest, source)):
        if inner.is_relative_to(container):
            path, outer = inner.relative_to(container), container
            while path.name == outer.name:
                path, outer = path.parent, outer.parent
            yield PathRule(path, include=False)
    if sync_state_path.is_relative_to(source):
        yield PathRule(sync_state_path.relative_to(source), include=False)


def resolve_sub_path(source: Path, sub_check_path: Path | None) -> Path | None:
    return (
        Path("")
        if sub_check_path is None
        else sub_check_path.relative_to(source)
        if sub_check_path.is_relative_to(source)
        else None
    )


def parse_rules(root: Path, includes: Entries, excludes: Entries) -> list[PathRule]:
    return [
        *(PathRule(path, include=True) for path in generate_paths(includes, root)),
        *(PathRule(path, include=False) for path in generate_paths(excludes, root)),
    ]


def generate_scoped_rules(rules: list[PathRule], sub_path: Path) -> Iterator[PathRule]:
    for rule in rules:
        if sub_path in rule.path.parents:
            yield rule
    yield PathRule(sub_path, include=Scope(rules).includes(str(sub_path)))
    for ancestor in sub_path.parents:
        yield PathRule(ancestor, include=False)


def generate_paths(entries: Entries, root: Path) -> Iterator[Path]:
    for entry in entries or ():
        names, content = (
            next(iter(entry.items())) if isinstance(entry, dict) else (entry, [])
        )
        path = resolve_names(names, root)
        if path is not None:
            children = generate_paths(content, root / path) if content else [Path()]
            yield from (path / child for child in children)


def resolve_names(names: str, root: Path) -> Path | None:
    path = Path()
    for part in (root / names).resolve().relative_to(root.resolve()).parts:
        path /= resolve_version(part, root / path)
    return None if version_placeholder in str(path) else path


def resolve_version(name: str, root: Path) -> str:
    prefix, versioned, _ = name.partition(version_placeholder)
    candidates = root.glob(f"{prefix}*") if versioned else ()
    latest = max(candidates, key=attrgetter("mtime"), default=None)
    return name if latest is None else latest.name
