import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field

import cli

from backup import backup
from backup.context import context
from backup.context.action import Action
from backup.models import Changes, Path
from backup.models.change import run_diff
from backup.utils import exporter

from . import cache, profile


@dataclass
class Backup(backup.Backup):
    confirm: bool = field(default_factory=lambda: context.options.confirm_push)

    def run_action(self, action: Action) -> None:
        match action:
            case Action.status:
                self.status()
            case Action.push:
                self.run_push()
            case Action.pull:
                self.run_pull()
            case Action.diff:
                self.diff()

    def status(self, *, show: bool = True) -> Changes:
        self.paths = self.scan_changes(quiet=True).paths
        status = super().capture_status() if self.paths else Changes()
        if show:
            status.print()
        return status

    def run_push(self, *, reverse: bool = False) -> None:
        any_include = any(rule.startswith("+") for rule in self.filter_rules)
        if not self.paths and not any_include:
            self.paths = self.check_changed_paths(reverse=reverse)
        if self.paths:
            if Path.HOME.is_relative_to(self.source):
                relative_home = Path.HOME.relative_to(self.source)
                home_paths = [
                    path.relative_to(relative_home)
                    for path in self.paths
                    if path.is_relative_to(relative_home)
                ]
                self.paths = [
                    path
                    for path in self.paths
                    if not path.is_relative_to(relative_home)
                ]
            else:
                home_paths = []
            if self.paths:
                self.start_push(reverse=reverse)
            if home_paths:
                self.paths = home_paths
                self.sub_check_path = relative_home
                self.start_push(reverse=reverse)

    def start_push(
        self,
        *,
        reverse: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        backup.Backup(
            paths=self.paths,
            sub_check_path=self.sub_check_path,
        ).push(reverse=reverse)
        return cache.Backup(
            paths=self.paths,
            sub_check_path=self.sub_check_path,
        ).push()

    def check_changed_paths(self, *, reverse: bool) -> list[Path]:
        changes: Changes = self.scan_changes(reverse=reverse)
        remove_changes = (
            changes
            and context.options.confirm_push
            and sys.stdin.isatty()
            and not self.ask_confirm(changes, reverse=reverse)
        )
        if remove_changes:
            changes.changes = []  # pragma: nocover
        return [
            change.source.relative_to(self.source) / change.path
            if change.source
            else change.path
            for change in changes.changes
        ]

    @classmethod
    def ask_confirm(cls, changes: Changes, *, reverse: bool = False) -> bool:
        message = "Pull?" if reverse else "Push?"
        response = changes.ask_confirm(
            message,
            show_diff=context.options.show_file_diffs,
        )
        if not response and not context.options.show_file_diffs:
            response = changes.ask_confirm(message, show_diff=True)  # pragma: nocover
        return response

    def scan_changes(self, *, quiet: bool = False, reverse: bool = False) -> Changes:
        if (
            context.profiles_source_root.is_relative_to(self.source)
            and Path.profile.exists()
        ):
            profile.Backup().capture_push()
        backup_ = cache.Backup(quiet=quiet, sub_check_path=self.sub_check_path)
        return backup_.status(reverse=reverse)

    def run_pull(self) -> None:
        if not context.options.no_sync:
            self.start_remote_sync()
        self.run_push(reverse=True)
        if self.paths:
            self.after_pull()

    def after_pull(self) -> None:
        if self.contains_change(Path.resume) and exporter.export_changes():
            path = Path.main_resume_pdf
            with cli.status("Uploading new resume pdf"):
                Backup(path=path, confirm=False).capture_push()
        if self.contains_change(context.profiles_path):
            profile.Backup().reload()

    def contains_change(self, path: Path) -> bool:
        change = False
        if path.is_relative_to(self.source):
            relative_path = path.relative_to(self.source)
            change = any(path.is_relative_to(relative_path) for path in self.paths)
        return change

    def start_remote_sync(self) -> None:
        message = self.get_sync_message()
        with cli.status(message):
            self.run_remote_sync()

    def get_sync_message(self) -> str:
        message = "Reading remote filesystem"
        if self.sub_check_path is not None:
            path = context.config.backup_source / self.sub_check_path
            message += f" at {path.resolve().short_notation}"
        return message

    def run_remote_sync(self) -> None:
        if not self.filter_rules:
            self.filter_rules = list(self.generate_pull_filters())
        info = self.get_dest_info()
        cache_backup = cache.Backup(
            sub_check_path=self.sub_check_path,
            filter_rules=self.filter_rules,
        )
        cache_backup.update_dest(info)
        self.create_filters()

    def generate_pull_filters(self) -> Iterator[str]:
        rules = cache.Backup(sub_check_path=self.sub_check_path).entry_rules()
        for rule in rules:
            sign = "+" if rule.include else "-"
            pattern = f"{sign} /{rule.path}"
            yield pattern
            yield f"{pattern}/**"
        yield "- /**"

    def diff(self, paths: list[Path] | None = None) -> None:
        if paths is None:
            status = self.status()
            paths = [
                change.path
                for change in status
                if context.options.diff_all
                or cli.confirm(f"Compare {change.message[2:-1]}?", default=True)
            ]
        if paths:
            for path in paths:
                cli.console.rule(str(path))
                sub_check_path = self.sub_check_path or ""
                run_diff(path, self.source, context.config.cache_path / sub_check_path)
