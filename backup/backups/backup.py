import sys
from dataclasses import dataclass

import cli

from .. import backup
from ..utils import Changes, Path, exporter
from . import cache, profile


@dataclass
class Backup(backup.Backup):
    quiet_cache: bool = False
    sync_remote: bool = True
    reverse: bool = False
    include_browser: bool = False
    confirm: bool = True

    def status(self):
        self.quiet_cache = True
        self.paths = self.cache_status().paths
        status = super().status() if self.paths else Changes()
        status.print()

    def push(self):
        paths = self.get_changed_paths()
        if paths:
            if self.reverse:
                self.check_root_paths(paths)
            backup.Backup(paths=paths, reverse=self.reverse).push()
            cache.Backup(paths=paths).push()

    def check_root_paths(self, paths):
        root_paths = []
        for path in paths:
            source_parent = self.source / path.parent
            if source_parent.parent.is_root():
                root_paths.append(path)
                paths.remove(path)

        if root_paths:
            self.process_root_paths(root_paths)

    def process_root_paths(self, paths: list[Path]):
        with Path.tempfile() as temp_dest:
            temp_dest.unlink()
            self.copy_with_intermediate(paths, temp_dest)

    def copy_with_intermediate(self, paths: list[Path], temp_dest: Path):
        backup.Backup(source=self.dest, dest=temp_dest, paths=paths).push()
        backup.Backup(source=temp_dest, dest=self.source, root=True, paths=paths).copy()

    def get_changed_paths(self):
        changes: Changes = self.cache_status()
        if changes and self.confirm and sys.stdin.isatty():
            self.check_confirm(changes)
        return changes.paths

    def cache_status(self) -> Changes:
        profile.Backup().copy()
        cache_backup = cache.Backup(
            quiet=self.quiet_cache,
            reverse=self.reverse,
            include_browser=self.include_browser,
        )
        return cache_backup.status()

    def check_confirm(self, changes: Changes):
        cli.console.clear()
        cli.console.rule("Backup")
        changes.print()
        message = "Pull?" if self.reverse else "Push?"
        if not cli.confirm(message, default=True):
            changes.changes = []

    def pull(self):
        if self.sync_remote:
            self.start_sync_remote()
        reverse_backup = Backup(
            reverse=True, include_browser=self.include_browser, confirm=self.confirm
        )
        reverse_backup.push()
        self.after_pull()

    @classmethod
    def after_pull(cls):
        profile.Backup().reload()
        exporter.export_changes()

    def start_sync_remote(self):
        self.create_filters()
        if not self.include_browser:
            self.filter_rules.append(f"- {cache.Entry.browser_pattern}")
        info = self.get_dest_info()
        cache_backup = cache.Backup(
            sub_check=self.sub_check, filter_rules=self.filter_rules
        )
        cache_backup.update_dest(info)
