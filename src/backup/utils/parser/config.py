from collections.abc import Iterator
from typing import Any, TypeVar, cast

from backup.context import context
from backup.models import (
    BackupConfig,
    Path,
    SerializedBackupConfig,
    SerializedEntryConfig,
)
from backup.syncer import SyncConfig, Syncer

from .rules import RuleParser

Entries = list[str | dict[str, "Entries"] | Any]


T = TypeVar("T")


class EntryParser:
    def __init__(self, config: SerializedBackupConfig) -> None:
        dest = config.source if config.dest == "/" else config.dest
        self.source = Path(config.source)
        self.dest = Path(dest)
        self.cache = Path(config.cache)
        self.cache.mkdir(parents=True, exist_ok=True)

    def parse_entry(self, entry: SerializedEntryConfig) -> BackupConfig:
        source = self.source / Path(entry.source)
        if source == Path("/") / "HOME":
            source = Path.HOME
        dest = Path(entry.dest)
        if dest.name == "__PROFILE__":
            dest = dest.with_name(context.storage.active_profile)
        if not context.options.include_browser:
            remove_browser(entry.includes, context.config.browser_name)
        sub_path = (
            Path("")
            if context.sub_check_path is None
            else context.sub_check_path.relative_to(source)
        )
        rules = RuleParser(
            source,
            sub_path,
            entry.includes,
            entry.excludes,
        ).parse_rules()
        return BackupConfig(
            source / sub_path,
            self.dest / dest / sub_path,
            self.cache / dest / sub_path,
            rules,
        )


def load_config() -> dict[str, Any]:
    if not Path.config.exists():
        Syncer(SyncConfig(directory=Path.config)).capture_pull()
    return cast("dict[str, Any]", context.storage.backup_config)


def parse_config(config_dict: dict[str, Any]) -> Iterator[BackupConfig]:
    config = SerializedBackupConfig.from_dict(config_dict)
    parser = EntryParser(config)
    for entry in config.syncs:
        parsed_entry = parser.parse_entry(entry)
        should_use = parsed_entry.source.exists() and any(
            rule.include for rule in parsed_entry.rules
        )
        if should_use:
            yield parsed_entry


def remove_browser(includes: list[str | dict[str, Any]], browser_name: str) -> None:
    for include in includes:
        if isinstance(include, dict):
            key, value = next(iter(include.items()))
            remove_browser(value, browser_name)
            if browser_name in key:
                includes.remove(include)


def extract_sub_entries(entries: Entries, path: Path) -> Entries:
    while path.parts and entries:
        entries = list(generate_sub_entries(entries, path))
        path = path.relative_to(Path(path.parts[0]))
    return entries


def generate_sub_entries(
    entries: Entries,
    path: Path,
) -> Iterator[str | dict[str, Any]]:
    name = path.parts[0]
    for entry in entries:
        entry_name = next(iter(entry.keys())) if isinstance(entry, dict) else entry
        if entry_name == ".":
            entry_name = ""
        entry_path = Path(entry_name)
        if not entry_name or entry_path.parts[0] == name:
            relative_name = (
                str(entry_path.relative_to(name)) if entry_name else entry_name
            )
            if isinstance(entry, str):
                yield relative_name
            else:
                sub_entries = next(iter(entry.values()))
                if entry_name == name:
                    yield from sub_entries
                else:
                    yield {relative_name: sub_entries}
