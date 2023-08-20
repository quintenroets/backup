import fnmatch
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property

import cli

from ..utils import Changes, Path, PathEntry, parser
from . import cache


@dataclass
class Backup(cache.Backup):
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
        generated_entries: Iterable[PathEntry] = self.generate_entries()
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
        path_structure = self.path_config()
        for relative_root, include in path_structure:
            source_root = self.source / relative_root
            if include:
                for source_path in source_root.find(exclude=self.exclude_root):
                    yield PathEntry(
                        source=source_path, include_browser=self.include_browser
                    )
            self.visited.add(source_root)

    def generate_dest_entries(self):
        for dest_path in self.dest.rglob("*"):
            yield PathEntry(dest=dest_path, include_browser=self.include_browser)

    def path_config(self):
        self.check_config_path()
        return parser.parse_paths_comb(self.include_dict, Path.paths_exclude.yaml)

    @classmethod
    def check_config_path(cls):
        if not Path.config.exists():
            Backup(folder=Path.config).pull()

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
            browser_pattern = f".config/{PathEntry.browser_name}/**/*"
            ignore_patterns.append(browser_pattern)
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
                if PathEntry.browser_name in key:
                    includes.remove(include)
