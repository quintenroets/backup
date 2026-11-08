from collections.abc import Iterable, Iterator
from operator import attrgetter
from typing import Any

from .models import BackupConfig, Entries, Path, PathRule, SerializedBackupConfig


def parse_config(raw: dict[str, Any], backup_root: Path) -> Iterator[BackupConfig]:
    config = SerializedBackupConfig.from_dict(raw)
    for sync in config.syncs:
        source = config.source / sync.source
        source = Path.HOME if source == Path("/HOME") else source
        root = source if source.is_relative_to(backup_root) else backup_root
        absolute_rules = (
            PathRule(resolve_pattern(pattern, source), include)
            for include, entries in ((True, sync.includes), (False, sync.excludes))
            for pattern in flatten(entries)
        )
        rules = list(make_relative(absolute_rules, root))
        if root.exists() and any(rule.include for rule in rules):
            path = sync.dest / root.relative_to(source)
            cache = config.cache / path
            yield BackupConfig(root, config.dest / path, cache, rules, config.ignores)


def make_relative(rules: Iterable[PathRule], root: Path) -> Iterator[PathRule]:
    ordered = sorted(rules, key=lambda rule: -len(rule.path.parts))
    for rule in ordered:
        if root in rule.path.parents:
            yield PathRule(rule.path.relative_to(root), rule.include)
    inherited = (rule.include for rule in ordered if root.is_relative_to(rule.path))
    yield PathRule(Path(), include=next(inherited, False))


def flatten(entries: Entries) -> Iterator[Path]:
    for entry in entries:
        items = entry.items() if isinstance(entry, dict) else ((entry, ()),)
        for pattern, content in items:
            for child in flatten(content) if content else (Path(),):
                yield Path(pattern) / child


def resolve_pattern(pattern: Path, source: Path) -> Path:
    path = source
    for part in pattern.parts:
        prefix, versioned, suffix = part.partition("__VERSION__")
        candidates = path.glob(f"{prefix}*{suffix}") if versioned else ()
        path = max(candidates, key=attrgetter("mtime"), default=path / part)
    return source / path.resolve().relative_to(source.resolve())
