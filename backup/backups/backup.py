import sys
from dataclasses import dataclass

import cli

from .. import backup
from ..utils import Changes, Path, differ, exporter
from . import cache, profile


@dataclass
class Backup(backup.Backup):
    quiet_cache: bool = False
    sync_remote: bool = True
    reverse: bool = False
    include_browser: bool = False
    confirm: bool = True
    show_diff: bool = False

    def status(self, show=True):
        self.quiet_cache = True
        self.paths = self.cache_status().paths
        status = super().status() if self.paths else Changes()
        if show:
            status.print()
        return status

    def push(self):
        if not self.paths:
            self.paths = self.get_changed_paths()
        if self.paths:
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
            if not self.ask_confirm(changes):
                changes.changes = []
        return changes.paths

    def ask_confirm(self, changes: Changes):
        message = "Pull?" if self.reverse else "Push?"
        response = changes.ask_confirm(message, show_diff=self.show_diff)
        if not response and not self.show_diff:
            response = changes.ask_confirm(message, show_diff=True)
        return response

    def cache_status(self) -> Changes:
        if profile.Backup.source.is_relative_to(self.source):
            profile.Backup().push()
        cache_backup = cache.Backup(
            quiet=self.quiet_cache,
            reverse=self.reverse,
            include_browser=self.include_browser,
            sub_check_path=self.sub_check_path,
        )
        return cache_backup.status()

    def pull(self):
        if self.sync_remote:
            self.start_remote_sync()
        self.start_pull()
        if self.paths:
            self.after_pull()

    def start_pull(self):
        backuper = Backup(
            paths=self.paths,
            quiet=self.quiet,
            quiet_cache=self.quiet_cache,
            sub_check_path=self.sub_check_path,
            reverse=True,
            include_browser=self.include_browser,
            confirm=self.confirm,
        )
        backuper.push()
        self.paths = backuper.paths

    def after_pull(self):
        if self.contains_change(Path.resume):
            if exporter.export_changes():
                path = Path.main_resume_pdf
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

    def start_remote_sync(self):
        message = self.get_sync_message()
        with cli.status(message):
            self.run_remote_sync()

    def get_sync_message(self) -> str:
        message = "Reading remote filesystem"
        if self.sub_check_path is not None:
            message += f" at {self.sub_check_path.short_notation}"
        return message

    def run_remote_sync(self):
        self.create_filters()
        if not self.include_browser:
            self.filter_rules.append(f"- {cache.Entry.browser_pattern}")
        info = self.get_dest_info()
        cache_backup = cache.Backup(
            sub_check_path=self.sub_check_path, filter_rules=self.filter_rules
        )
        cache_backup.update_dest(info)

    def diff(self, paths=None, diff_all=False):
        if paths is None:
            status = self.status()
            paths = [
                change.path
                for change in status
                if diff_all
                or cli.confirm(f"Compare {change.message[2:-1]}?", default=True)
            ]
        if paths:
            for path in paths:
                cli.console.rule(str(path))
                sub_check_path = self.sub_check_path or ""
                differ.run_diff(path, self.source, cache.Backup.dest / sub_check_path)
