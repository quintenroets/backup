import fnmatch
from backup.rclone import Rclone, RcloneConfig
from dataclasses import dataclass, field
from functools import cached_property

from backup.context import context
from backup.models import Changes, Path, BackupConfig
from backup.utils import parser
from backup.utils.parser import Rules

from .cache.detailed_entry import Entry
from typing import Any, Iterator


@dataclass
class CacheScanner:
    backup_config: BackupConfig
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    entries: set[Entry] = field(default_factory=set)

    @property
    def config(self) -> RcloneConfig:
        dest = context.extract_cache_path()
        return RcloneConfig(
            source=self.backup_config.source, dest=dest / self.backup_config.dest
        )

    def calculate_changes(self, *, reverse: bool = False) -> Changes:
        paths = [
            path
            for entry in self.entries
            for path in entry.get_paths()
            if entry.is_changed()
        ]
        return (
            Rclone(self.config.with_paths(paths)).capture_status(reverse=reverse)
            if paths
            else Changes()
        )

    def generate_entries(self) -> Iterator[Entry]:
        rules = self.entry_rules()
        for rule in rules:
            source_path = self.config.source / rule.path
            dest_path = self.config.dest / rule.path
            if rule.include:
                is_file = source_path.is_file() or dest_path.is_file()
                if is_file:
                    if source_path.exists():
                        yield self.create_entry(source=source_path)
                    else:
                        yield self.create_entry(dest=dest_path)
                else:
                    for entry_path in source_path.find(exclude=self.exclude_root):
                        yield self.create_entry(source=entry_path)
                    for entry_path in dest_path.find(
                        exclude=lambda path_: path_ in self.visited
                    ):
                        yield self.create_entry(dest=entry_path)
            self.visited.add(source_path)
            self.visited.add(dest_path)

    def create_entry(self, **kwargs: Any) -> Entry:
        return Entry(self.config.source, self.config.dest, **kwargs)

    def entry_rules(self) -> Iterator[parser.PathRule]:
        any_include = False
        rules = self.generate_entry_rules()
        for rule in rules:
            any_include |= rule.include
            yield rule
        # include everything else if no include rules
        yield parser.PathRule(Path(), include=False)

    def generate_entry_rules(self) -> Iterator[parser.PathRule]:
        rules = Rules(
            self.backup_config.includes,
            self.backup_config.excludes,
            self.backup_config.source,
        ).rules
        self.check_config_path()
        if self.config.overlapping_sub_path is not None:
            path = context.config.cache_path.relative_to(Path("/"))
            rules.insert(0, parser.PathRule(path, include=False))
        if self.config.sub_check_path is not None:
            relative_source = self.config.source.relative_to(self.config.source)
            for rule in rules:
                if rule.path.is_relative_to(relative_source):
                    rule.path = rule.path.relative_to(relative_source)
                    yield rule
        else:
            yield from rules

    @classmethod
    def check_config_path(cls) -> None:
        if not Path.config.exists():
            Rclone(RcloneConfig(directory=Path.config)).capture_pull()

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or any(
                fnmatch.fnmatch(str(path), pattern) for pattern in self.ignore_patterns
            )
            or path.name in context.storage.ignore_names
            or path.is_symlink()
        )

    @cached_property
    def ignore_patterns(self) -> list[str]:
        ignore_patterns = context.storage.ignore_patterns
        if not context.options.include_browser:
            ignore_patterns.append(context.config.browser_pattern)
        return ignore_patterns
