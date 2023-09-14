import sys
from dataclasses import dataclass

import cli

from .. import backup
from ..utils import Changes, Path, exporter, piper
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
        if not self.paths:
            self.paths = self.cache_status().paths
            status = super().status() if self.paths else Changes()
            status.print()
        else:
            for path in self.paths:
                self.differ(path)

    def differ(self, path):
        cli.console.rule(str(path))
        source = self.source / path
        dest = cache.Backup.dest / self.sub_check_path / path
        commands = (("diff", "-u", dest, source), ("colordiff",), ("grep", "-v", path))
        return piper.run(commands)

    def push(self):
        if not self.paths:
            self.paths = self.get_changed_paths()
        if self.paths:
            if self.reverse:
                self.pull_root_paths()
            self.start_push()

    def start_push(self):
        kwargs = dict(
            path=self.path, paths=self.paths, sub_check_path=self.sub_check_path
        )
        backups = (
            backup.Backup(reverse=self.reverse, quiet=self.quiet, **kwargs),
            cache.Backup(**kwargs),
        )
        for push_backup in backups:
            push_backup.push()

    def get_changed_paths(self):
        changes: Changes = self.cache_status()
        if changes and self.confirm and sys.stdin.isatty():
            self.check_confirm(changes)
        return changes.paths

    def cache_status(self) -> Changes:
        if profile.Backup.source.is_relative_to(self.source):
            profile.Backup().copy()
        cache_backup = cache.Backup(
            quiet=self.quiet_cache,
            reverse=self.reverse,
            include_browser=self.include_browser,
            sub_check_path=self.sub_check_path,
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
            reverse=True,
            include_browser=self.include_browser,
            confirm=self.confirm,
            sub_check_path=self.sub_check_path,
        )
        reverse_backup.push()
        if reverse_backup.paths:
            self.paths = reverse_backup.paths
            self.after_pull()

    def after_pull(self):
        if self.contains_change(Path.resume):
            if exporter.export_changes():
                path = Path.main_resume_pdf.relative_to(Backup.source)
                with cli.status("Uploading new resume pdf"):
                    Backup(path=path, confirm=False, quiet=True).start_push()
        if self.contains_change(Path.profiles):
            profile.Backup().reload()

    def contains_change(self, path: Path):
        change = False
        if path.is_relative_to(self.source):
            relative_path = path.relative_to(self.source)
            change = any(path.is_relative_to(relative_path) for path in self.paths)
        return change

    def start_sync_remote(self):
        self.create_filters()
        if not self.include_browser:
            self.filter_rules.append(f"- {cache.Entry.browser_pattern}")
        info = self.get_dest_info()
        cache_backup = cache.Backup(
            sub_check_path=self.sub_check_path, filter_rules=self.filter_rules
        )
        cache_backup.update_dest(info)
