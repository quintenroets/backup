from typing import Iterator

from backup.models import Path, BackupConfig, Entries

from backup.context import context
from dataclasses import dataclass, field
from package_utils.dataclasses.mixins import SerializationMixin

from typing import Any


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
            yield BackupConfig(source, dest, config.includes, config.excludes)


def remove_browser(includes: list[str | dict[str, Any]], browser_name: str) -> None:
    for include in includes:
        if isinstance(include, dict):
            key, value = next(iter(include.items()))
            remove_browser(value, browser_name)
            if browser_name in key:
                includes.remove(include)
