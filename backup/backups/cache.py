from dataclasses import dataclass, field
from functools import cached_property

import cli

from .. import backup
from ..utils import Changes, Path, custom_checker, parser
from . import cache_to_remote


@dataclass
class Backup(backup.Backup):
    quiet: bool = True
    dest: Path = Path.backup_cache
    updated: bool = False
    visited: set = field(default_factory=set)

    def __post_init__(self):
        if not self.dest.exists():
            self.create_dest()
        self.ignore_names = Path.ignore_names.yaml
        self.ignore_patterns = Path.ignore_patterns.yaml
        self.ignore_paths = {
            path for pattern in self.ignore_patterns for path in Path.HOME.glob(pattern)
        }
        super().__post_init__()

    def create_dest(self):
        commands = (f"mkdir {self.dest}", f"chown -R $(whoami):$(whoami) {self.dest}")
        cli.sh(*commands, root=True)
        cache_to_remote.Backup().pull()

    def status(self):
        self.paths = self.get_changed_paths()
        return super().status() if self.paths else Changes([])

    def get_changed_paths(self):
        paths = self.generate_changed_paths()
        paths = set(paths)
        return custom_checker.reduce(paths)

    def generate_changed_paths(self):
        generated_paths = self.generate_paths()
        path_pairs = set(generated_paths)

        for source_path, dest_path, relative_path in path_pairs:
            if source_path.mtime != dest_path.mtime:
                if not source_path.exists() or not source_path.tag:
                    yield relative_path

    def generate_paths(self):
        yield from self.generate_source_paths()
        # yield from self.generate_dest_paths()

    def generate_source_paths(self):
        path_structure = self.path_config()
        for relative_root, include in path_structure:
            source_root = self.source / relative_root
            if include:
                for source_path in source_root.find(exclude=self.exclude):
                    if source_path.is_file():
                        relative_path = source_path.relative_to(self.source)
                        dest_path = self.dest / relative_path
                        yield source_path, dest_path, relative_path

            self.visited.add(source_root)

    def generate_dest_paths(self):
        volatile_items = self.load_volatile()
        for dest_path in self.dest.find():
            if dest_path.is_file():
                relative_path = dest_path.relative_to(self.dest)
                if relative_path not in volatile_items:
                    source_path = self.source / relative_path
                    yield source_path, dest_path, relative_path

    @classmethod
    def load_volatile(cls):
        return tuple(
            volatile[0]
            for volatile in parser.parse_paths_comb(Path.paths_volatile.yaml, {})
        )

    def path_config(self):
        self.check_config_path()
        return parser.parse_paths_comb(self.include_dict, Path.paths_exclude.yaml)

    @classmethod
    def check_config_path(cls):
        if not Path.config.exists():
            Backup(folder=Path.config).pull()

    @cached_property
    def include_dict(self):
        includes = Path.paths_include.yaml
        remove_browser(includes)
        return includes

    def exclude(self, path: Path):
        return (
            path in self.ignore_paths
            or path in self.visited
            or path.name in self.ignore_names
            or (path / ".git").exists()
            or path.is_symlink()
            or (path.stat().st_size > 50 * 10**6 and path.suffix != ".zip")
            or path.suffix == ".part"
        )


def remove_browser(includes: list[str | dict]):
    browser_name = "chromium"
    for include in includes:
        if isinstance(include, dict):
            key, value = next(iter(include.items()))
            remove_browser(value)
            if browser_name in key:
                includes.remove(include)
