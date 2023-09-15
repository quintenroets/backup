import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property

import cli

from ...utils import Changes, Path, parser
from ..backup import backup
from . import raw
from .entry import Entry


@dataclass
class Backup(raw.Backup):
    quiet: bool = True
    visited: set = field(default_factory=set)
    include_browser: bool = True
    entry_count: int = 0

    def status(self):
        self.paths = self.get_changed_paths()
        return super().status() if self.paths else Changes([])

    def get_changed_paths(self):
        paths = self.generate_changed_paths()
        return list(paths)

    def generate_changed_paths(self):
        generated_entries: Iterable[Entry] = self.generate_entries()
        total = int(Path.number_of_paths.text or 0)
        generated_entries = cli.progress(
            generated_entries, description="Checking", unit="Files", total=total
        )
        path_entries = set(generated_entries)
        for entry in path_entries:
            if entry.is_changed():
                yield from entry.get_paths()

    def generate_entries(self):
        for path in self.generate_paths():
            yield path
            self.entry_count += 1
        Path.number_of_paths.text = self.entry_count

    def generate_paths(self):
        yield from self.generate_source_entries()
        yield from self.generate_dest_entries()

    def generate_source_entries(self):
        source = self.dest if self.reverse else self.source
        rules = self.entry_rules()
        for rule in rules:
            path = source / rule.path
            if rule.include:
                for source_path in path.find(exclude=self.exclude_root):
                    yield self.create_entry(source=source_path)
            self.visited.add(path)

    def generate_dest_entries(self):
        dest = self.source if self.reverse else self.dest
        for dest_path in dest.rglob("*"):
            yield self.create_entry(dest=dest_path)

    def create_entry(self, **kwargs):
        source = self.dest if self.reverse else self.source
        dest = self.source if self.reverse else self.dest
        return Entry(source, dest, include_browser=self.include_browser, **kwargs)

    def entry_rules(self):
        rules = self.generate_entry_rules()
        rules = list(rules)
        if not any(rule.include for rule in rules):
            # include everything else if no include rules
            root = Path()
            rule = parser.PathRule(root, True)
            rules.append(rule)
        return rules

    def generate_entry_rules(self):
        self.check_config_path()
        config_root = Backup.source
        rules = parser.Rules(
            self.include_dict, Path.paths_exclude.yaml, root=config_root
        )
        if self.sub_check_path is not None:
            relative_source = self.source.relative_to(config_root)
            for rule in rules:
                if rule.path.is_relative_to(relative_source):
                    rule.path = rule.path.relative_to(relative_source)
                    yield rule
        else:
            yield from rules

    @classmethod
    def check_config_path(cls):
        if not Path.config.exists():
            backup.Backup(folder=Path.config, quiet=True).pull()

    def exclude_root(self, path: Path):
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
    def ignore_patterns(self):
        ignore_patterns = Path.ignore_patterns.yaml
        if not self.include_browser:
            ignore_patterns.append(Entry.browser_pattern)
        return ignore_patterns

    @cached_property
    def ignore_names(self):
        return Path.ignore_names.yaml

    @cached_property
    def include_dict(self):
        includes = Path.paths_include.yaml
        if not self.include_browser:
            self.remove_browser(includes)
        return includes

    def remove_browser(self, includes: list[str | dict]):
        for include in includes:
            if isinstance(include, dict):
                key, value = next(iter(include.items()))
                self.remove_browser(value)
                if Entry.browser_name in key:
                    includes.remove(include)
