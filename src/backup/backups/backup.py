import subprocess
import sys
from dataclasses import dataclass, field

import cli

from backup import backup
from backup.context import context
from backup.models import Action, Changes, Path
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
        self.paths = self.cache_status(quiet=True).paths
        status = super().capture_status() if self.paths else Changes()
        if show:
            status.print()
        return status

    def run_push(self, *, reverse: bool = False) -> None:
        any_include = any(rule.startswith("+") for rule in self.filter_rules)
        if not self.paths and not any_include:
            self.paths = self.check_changed_paths(reverse=reverse)
        if self.paths:
            self.start_push(reverse=reverse)

    def start_push(
        self,
        *,
        reverse: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        backup.Backup(
            path=self.path,
            paths=self.paths,
            sub_check_path=self.sub_check_path,
        ).push(reverse=reverse)
        return cache.Backup(
            path=self.path,
            paths=self.paths,
            sub_check_path=self.sub_check_path,
        ).push()

    def check_changed_paths(self, *, reverse: bool) -> list[Path]:
        changes: Changes = self.cache_status(reverse=reverse)
        remove_changes = (
            changes
            and context.options.confirm_push
            and sys.stdin.isatty()
            and not self.ask_confirm(changes, reverse=reverse)
        )
        if remove_changes:
            changes.changes = []  # pragma: nocover
        return changes.paths

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

    def cache_status(self, *, quiet: bool = False, reverse: bool = False) -> Changes:
        if context.profiles_source_root.is_relative_to(self.source):
            profile.Backup().capture_push()
        cache_backup = cache.Backup(quiet=quiet, sub_check_path=self.sub_check_path)
        return cache_backup.status(reverse=reverse)

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
            message += f" at {self.sub_check_path.resolve().short_notation}"
        return message

    def run_remote_sync(self) -> None:
        if not self.filter_rules:
            self.create_filters()
        if not context.options.include_browser:
            self.filter_rules.append(f"- {context.config.browser_pattern}")
        info = self.get_dest_info()
        cache_backup = cache.Backup(
            sub_check_path=self.sub_check_path,
            filter_rules=self.filter_rules,
        )
        cache_backup.update_dest(info)

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
