import fnmatch
import typing
from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from functools import cached_property
from typing import Any

import cli

from ...models import Changes, Path
from ...utils import parser
from ..backup import backup
from . import raw
from .detailed_entry import Entry


@dataclass
class Backup(raw.Backup):
    quiet: bool = True
    visited: set[Path] = field(default_factory=set)
    include_browser: bool = True
    entry_count: int = 0

    def status(self) -> Changes:
        self.paths = self.get_changed_paths()
        return super().capture_status() if self.paths else Changes([])

    def get_changed_paths(self) -> list[Path]:
        paths = self.generate_changed_paths()
        return list(paths)

    def generate_changed_paths(self) -> Iterator[Path]:
        generated_entries: Iterable[Entry] = self.generate_entries()
        total = int(Path.number_of_paths.text or 0)
        generated_entries = cli.track_progress(
            generated_entries, description="Checking", unit="Files", total=total
        )
        path_entries = set(generated_entries)
        for entry in path_entries:
            if entry.is_changed():
                yield from entry.get_paths()

    def generate_entries(self) -> Iterator[Entry]:
        for path in self.generate_path_entries():
            yield path
            self.entry_count += 1
        Path.number_of_paths.text = self.entry_count

    def generate_path_entries(self) -> Iterator[Entry]:
        yield from self.generate_source_entries()
        yield from self.generate_dest_entries()

    def generate_source_entries(self) -> Iterator[Entry]:
        rules = self.entry_rules()
        for rule in rules:
            path = self.original_source / rule.path
            if rule.include:
                for source_path in path.find(exclude=self.exclude_root):
                    yield self.create_entry(source=source_path)
            self.visited.add(path)

    def generate_dest_entries(self) -> Iterator[Entry]:
        dest = self.source if self.reverse else self.dest
        for dest_path in dest.rglob("*"):
            yield self.create_entry(dest=dest_path)

    def create_entry(self, **kwargs: Any) -> Entry:
        source = self.dest if self.reverse else self.source
        dest = self.source if self.reverse else self.dest
        return Entry(source, dest, include_browser=self.include_browser, **kwargs)

    def entry_rules(self) -> Iterator[parser.PathRule]:
        any_include = False
        rules = self.generate_entry_rules()
        for rule in rules:
            any_include |= rule.include
            yield rule
        if not any_include:
            # include everything else if no include rules
            root = Path()
            yield parser.PathRule(root, True)

    def generate_entry_rules(self) -> Iterator[parser.PathRule]:
        self.check_config_path()
        config_root = Path(Backup.source)
        rules = parser.Rules(
            self.include_dict, Path.paths_exclude.yaml, root=config_root
        )
        if self.sub_check_path is not None:
            relative_source = self.original_source.relative_to(config_root)
            for rule in rules:
                if rule.path.is_relative_to(relative_source):
                    rule.path = rule.path.relative_to(relative_source)
                    yield rule
        else:
            yield from rules

    @classmethod
    def check_config_path(cls) -> None:
        if not Path.config.exists():
            backup.Backup(folder=Path.config).capture_pull()

    def exclude_root(self, path: Path) -> bool:
        return (
            path in self.visited
            or (path / ".git").exists()
            or any(
                fnmatch.fnmatch(str(path), pattern) for pattern in self.ignore_patterns
            )
            or path.name in self.ignore_names
            or path.is_symlink()
        )

    @cached_property
    def ignore_patterns(self) -> list[str]:
        ignore_patterns = typing.cast(list[str], Path.ignore_patterns.yaml)
        if not self.include_browser:
            ignore_patterns.append(Entry.browser_pattern)
        return ignore_patterns

    @cached_property
    def ignore_names(self) -> list[str]:
        return typing.cast(list[str], Path.ignore_names.yaml)

    @cached_property
    def include_dict(self) -> list[str | dict[str, Any]]:
        includes = Path.paths_include.yaml
        if not self.include_browser:
            self.remove_browser(includes)
        return typing.cast(list[str | dict[str, Any]], includes)

    def remove_browser(self, includes: list[str | dict[str, Any]]) -> None:
        for include in includes:
            if isinstance(include, dict):
                key, value = next(iter(include.items()))
                self.remove_browser(value)
                if Entry.browser_name in key:
                    includes.remove(include)
