from collections.abc import Iterator
from typing import Any, cast

from backup.context import context
from backup.models import (
    BackupConfig,
    Path,
    SerializedBackupConfig,
    SerializedEntryConfig,
)
from backup.syncer import create_syncer

from .rules import RuleParser


def resolve_sub_path(source: Path) -> Path:
    return (
        Path("")
        if context.sub_check_path is None
        else context.sub_check_path.relative_to(source)
        if context.sub_check_path.is_relative_to(source)
        else Path("__no_sub_match__")
    )


class EntryParser:
    def __init__(self, config: SerializedBackupConfig) -> None:
        dest = config.source if config.dest == "/" else config.dest
        self.source = Path(config.source)
        self.dest = Path(dest)
        self.cache = Path(config.cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.ignores = config.ignores

    def parse_entry(self, entry: SerializedEntryConfig) -> BackupConfig:
        source = self.source / Path(entry.source)
        if source == Path("/") / "HOME":
            source = Path.HOME
        dest = Path(entry.dest)
        sub_path = resolve_sub_path(source)
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
            self.ignores,
        )


def load_config() -> dict[str, Any]:
    if not Path.config.exists():
        create_syncer(directory=Path.config).capture_pull()
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
