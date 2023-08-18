import sys
from dataclasses import dataclass
from datetime import datetime, timezone

import cli

from .. import backup
from ..utils import Change, Changes, Path, exporter
from . import cache, profile, remote


@dataclass
class Backup(backup.Backup):
    quiet_cache: bool = False
    sync_remote: bool = True
    sub_check: bool = False
    reverse: bool = False

    def __post_init__(self):
        super().__post_init__()

    def status(self):
        self.quiet_cache = True
        self.paths = self.cache_status().paths
        status = super().status()
        status.print()

    def cache_status(self) -> Changes:
        profile.Backup().copy()
        return cache.Backup(quiet=self.quiet_cache).status()

    def push(self):
        paths = self.get_changed_paths()
        if paths:
            remote.Backup(paths=paths, reverse=self.reverse).push()
            cache.Backup(paths=paths).push()

    def get_changed_paths(self):
        changes: Changes = self.cache_status()
        if changes:
            changes = self.remove_excludes(changes)
        if changes:
            is_interactive = sys.stdin.isatty()
            if is_interactive:
                cli.console.clear()
                cli.console.rule("Backup")
                changes.print()
                message = "Pull?" if self.reverse else "Push?"
                if not cli.confirm(message, default=True):
                    changes.changes = []

        return changes.paths

    @classmethod
    def remove_excludes(cls, changes: Changes) -> Changes:
        config = cache.Backup().path_config()
        include_paths = [config_path for config_path, include in config if include]

        def is_include(change: Change):
            return any([change.path.is_relative_to(path) for path in include_paths])

        changes = [change for change in changes if is_include(change)]
        return Changes(changes)

    def pull(self):
        if self.sync_remote:
            self.start_sync_remote()
        self.reverse = True
        self.push()
        self.after_pull()

    def start_sync_remote(self):
        sub_path = Path.cwd().relative_to(Path.HOME) if self.sub_check else ""
        present = set({})

        def extract_tuple(date: datetime):
            # drive only remote minute precision and month range
            return date.month, date.day, date.hour, date.minute

        def are_equal(date1: datetime, date2: datetime):
            return extract_tuple(date1) == extract_tuple(date2)

        # set cache to remote mod time
        for path_str, date in self.get_remote_info(sub_path):
            cache_path = Path.backup_cache / sub_path / path_str
            cache_date = datetime.fromtimestamp(cache_path.mtime)
            cache_date = cache_date.astimezone(timezone.utc)

            if not are_equal(cache_date, date) or not cache_path.exists():
                mtime = cache_path.mtime + 1
                original_path = Path.HOME / cache_path.relative_to(Path.backup_cache)
                cache_path.text = "" if original_path.size else " "
                cache_path.touch(mtime=mtime)
            present.add(cache_path)

        def is_deleted(p: Path):
            return p.is_file() and p not in present

        sub_cache = Path.backup_cache / sub_path
        for path in sub_cache.find(is_deleted, recurse_on_match=True):
            # delete cache items not in remote
            path.unlink()

    @classmethod
    def get_remote_info(cls, sub_path):
        options = ("--all", "--modtime", "--noreport", "--full-path")
        command = "rclone tree"
        args = (command, options, Path.remote / sub_path)
        rclone_command = cli.prepare_args(args, command=True)[0]
        remove_color_command = r"sed 's/\x1B\[[0-9;]*[JKmsu]//g'"
        command = f"{rclone_command} | {remove_color_command}"
        with cli.status("Getting remote info"):
            lines = cli.lines(command, shell=True)

        date_start = "── ["
        date_end = "]  /"

        for line in lines:
            contains_date = date_start in line
            if contains_date:
                date_str, path_str = line.split(date_start)[1].split(date_end)
                date = datetime.strptime(date_str, "%b %d %H:%M")
                yield path_str, date

    @classmethod
    def after_pull(cls):
        profile.Backup().reload()
        exporter.export_changes()
