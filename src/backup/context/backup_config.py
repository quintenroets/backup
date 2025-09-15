from typing import Iterator
from backup.utils.parser import Rules

from backup.models import Path

from dataclasses import dataclass, field
from package_utils.dataclasses.mixins import SerializationMixin

from typing import Any

Entries = list[str | dict[str, "Entries"] | Any]


@dataclass
class BackupConfig:
    source: Path
    dest: Path
    rules: Rules


@dataclass
class BackupConfigSerialized(SerializationMixin):
    source: str | None = None
    dest: str | None = None
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)


def load_config(
    backups: list[Any], active_profile: str, include_browser: bool, browser_name: str
) -> Iterator[BackupConfig]:
    for item in backups:
        config = BackupConfigSerialized.from_dict(item)
        source = Path.HOME if config.source == "/HOME" else Path(config.source)
        if source.exists():
            dest = (
                source.relative_to(Path("/"))
                if config.dest is None
                else Path(config.dest)
            )
            if dest.name == "__PROFILE__":
                dest = dest.with_name(active_profile)
            if not include_browser:
                remove_browser(config.includes, browser_name)
            rules = Rules(config.includes, config.excludes, source)
            yield BackupConfig(source, dest, rules)


def remove_browser(includes: list[str | dict[str, Any]], browser_name: str) -> None:
    for include in includes:
        if isinstance(include, dict):
            key, value = next(iter(include.items()))
            remove_browser(value, browser_name)
            if browser_name in key:
                includes.remove(include)
