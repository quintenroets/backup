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
            self.check_confirm(changes)
        return changes.paths

    def check_confirm(self, changes: Changes):
        message = "Pull?" if self.reverse else "Push?"
        response = changes.ask_confirm(message)
        if not response:
            if cli.confirm("Compare?", default=True):
                print("\n")
                self.paths = [change.path for change in changes]
                self.diff()
                response = changes.ask_confirm("\n" + message, show=False)

        if not response:
            changes.changes = []

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

    def diff(self, diff_all=False):
        if not self.paths:
            status = self.status()
            self.paths = [
                change.path
                for change in status
                if diff_all
                or cli.confirm(f"Compare {change.message[2:-1]}?", default=True)
            ]
        if self.paths:
            for path in self.paths:
                self.differ(path)

    def differ(self, path):
        cli.console.rule(str(path))
        source = self.source / path
        sub_check_path = self.sub_check_path or ""
        dest = cache.Backup.dest / sub_check_path / path
        commands = (("diff", "-u", dest, source), ("colordiff",), ("grep", "-v", path))
        return piper.run(commands)
