from __future__ import annotations

import typing
from typing import Any

from backup.syncer import PathRule, resolve_rules

from .models import (
    BackupConfig,
    Config,
    Entries,
    Path,
    Scope,
    SerializedEntryConfig,
    SyncRecords,
    SyncState,
    resolve_overlapping_sub_path,
)

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover

    import superpathlib  # pragma: nocover

Entry = str | tuple[str, ...] | dict[Any, Any]
version_keyword = "__VERSION__"


def parse_config(
    config: Config,
    sync_state: SyncState,
    sub_check_path: Path | None = None,
) -> Iterator[BackupConfig]:
    for entry in config.syncs:
        source = resolve_source(Path(config.source) / Path(entry.source))
        sub_path = resolve_sub_path(source, sub_check_path)
        if sub_path is not None:
            parsed_entry = parse_entry(entry, config, sync_state, source, sub_path)
            should_use = parsed_entry.source.exists() and any(
                rule.include for rule in parsed_entry.scope.rules
            )
            if should_use:
                yield parsed_entry


def parse_entry(
    entry: SerializedEntryConfig,
    config: Config,
    sync_state: SyncState,
    source: Path,
    sub_path: Path,
) -> BackupConfig:
    root_dest = Path(config.source if config.dest == "/" else config.dest)
    dest = Path(entry.dest)
    scanned_source = source / sub_path
    scanned_dest = root_dest / dest / sub_path
    rules = [
        *generate_owned_exclusions(scanned_source, scanned_dest, sync_state.path),
        *parse_rules(source, sub_path, entry.includes, entry.excludes),
    ]
    return BackupConfig(
        scanned_source,
        scanned_dest,
        SyncRecords(sync_state, dest / sub_path),
        Scope(rules, config.ignores, sub_path, config.max_backup_size),
        config.rclone,
    )


def generate_owned_exclusions(
    source: Path,
    dest: Path,
    sync_state_path: Path,
) -> Iterator[PathRule]:
    overlap = resolve_overlapping_sub_path(source, dest)
    if overlap is not None:
        yield PathRule(Path(overlap), include=False)
    if sync_state_path.is_relative_to(source):
        yield PathRule(sync_state_path.relative_to(source), include=False)


def resolve_source(source: Path) -> Path:
    return Path.HOME if source == Path("/HOME") else source


def resolve_sub_path(source: Path, sub_check_path: Path | None) -> Path | None:
    return (
        Path("")
        if sub_check_path is None
        else sub_check_path.relative_to(source)
        if sub_check_path.is_relative_to(source)
        else None
    )


def parse_rules(
    root: Path,
    sub_path: Path,
    includes: Entries,
    excludes: Entries,
) -> list[PathRule]:
    rules = [
        *generate_rules(includes, root, include=True),
        *generate_rules(excludes, root, include=False),
    ]
    return list(generate_scoped_rules(rules, sub_path))


def generate_scoped_rules(rules: list[PathRule], sub_path: Path) -> Iterator[PathRule]:
    for rule in rules:
        if rule.path.is_relative_to(sub_path):
            yield PathRule(rule.path.relative_to(sub_path), rule.include)
    yield resolve_root_rule(rules, sub_path)


def resolve_root_rule(rules: list[PathRule], sub_path: Path) -> PathRule:
    containers = [rule for rule in rules if strictly_contains(rule.path, sub_path)]
    deepest_first = resolve_rules(containers)
    return PathRule(Path(), include=bool(deepest_first) and deepest_first[0].include)


def strictly_contains(path: superpathlib.Path, sub_path: Path) -> bool:
    return path != sub_path and sub_path.is_relative_to(path)


def generate_rules(
    entries: Entries,
    root: Path,
    *,
    include: bool,
) -> Iterator[PathRule]:
    for entry in entries or ():
        yield from generate_entry_rules(entry, root, include=include)


def generate_entry_rules(
    entry: Entry,
    root: Path,
    *,
    include: bool,
) -> Iterator[PathRule]:
    names, content = (
        next(iter(entry.items())) if isinstance(entry, dict) else (entry, [])
    )
    parts = resolve_parts(names, root) if isinstance(names, str) else list(names)
    name = parse_name(parts[0], root)
    if name is not None:
        sub_entries = [{tuple(parts[1:]): content}] if len(parts) > 1 else content
        if sub_entries:
            for rule in generate_rules(sub_entries, root / name, include=include):
                yield PathRule(Path(name) / rule.path, include)
        else:
            yield PathRule(Path(name), include)


def resolve_parts(names: str, root: Path) -> list[str]:
    path = (root / names).resolve()
    resolved_root = root.resolve()
    if not path.is_relative_to(resolved_root):  # pragma: no cover
        message = "Currently, only symlinks under the same sub root are allowed"
        raise ValueError(message)
    return str(path.relative_to(resolved_root)).split("/")


def parse_name(name: str, root: Path) -> str | None:
    resolved: str | None = name
    if version_keyword in name:
        name_start = name.split(version_keyword, maxsplit=1)[0]
        paths = sorted(root.glob(f"{name_start}*"), key=lambda path: -path.mtime)
        resolved = paths[0].name if paths else None
    return resolved
