import sys
from dataclasses import dataclass

import cli

from ..utils import Changes, exporter
from . import profile, remote, smart_cache


@dataclass
class Backup(remote.Backup):
    quiet_cache: bool = False
    sync_remote: bool = True
    reverse: bool = False
    include_browser: bool = True

    def status(self):
        self.quiet_cache = True
        self.paths = self.cache_status().paths
        status = super().status() if self.paths else Changes()
        status.print()

    def push(self):
        paths = self.get_changed_paths()
        if paths:
            remote.Backup(paths=paths, reverse=self.reverse).push()
            smart_cache.Backup(paths=paths).push()

    def get_changed_paths(self):
        changes: Changes = self.cache_status()
        if changes and sys.stdin.isatty():
            self.check_confirm(changes)
        return changes.paths

    def cache_status(self) -> Changes:
        profile.Backup().copy()
        cache_backup = smart_cache.Backup(
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
        Backup(reverse=True).push()
        self.after_pull()

    @classmethod
    def after_pull(cls):
        profile.Backup().reload()
        exporter.export_changes()

    def start_sync_remote(self):
        dest_info = self.get_dest_info()
        smart_cache.Backup(sub_check=self.sub_check).update_dest(dest_info)
