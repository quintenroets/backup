from typing import Iterator

from backup.models import Path, BackupConfig, Entries

from backup.context import context
from dataclasses import dataclass, field
from package_utils.dataclasses.mixins import SerializationMixin

from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class BackupConfigSerialized(SerializationMixin):
    source: str | None = None
    dest: str | None = None
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


def load_config() -> Iterator[BackupConfig]:
    for item in context.storage.backup_config:
        config = BackupConfigSerialized.from_dict(item)
        source = Path.HOME if config.source == "/HOME" else Path(config.source)
        if source.exists():
            dest = (
                source.relative_to(Path("/"))
                if config.dest is None
                else Path(config.dest)
            )
            if dest.name == "__PROFILE__":
                dest = dest.with_name(context.storage.active_profile)
            if not context.options.include_browser:
                remove_browser(config.includes, context.config.browser_name)
            if context.sub_check_path is not None:
                sub_path = context.sub_check_path.relative_to(source)
                config.includes = extract_sub_entries(config.includes, sub_path)
                config.excludes = extract_sub_entries(config.excludes, sub_path)
                source /= sub_path
                dest /= sub_path
            if config.includes:
                yield BackupConfig(source, dest, config.includes, config.excludes)


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


def generate_sub_entries(entries: Entries, path: Path) -> Entries:
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
