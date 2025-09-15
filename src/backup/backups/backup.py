import subprocess
from backup.utils.itertools import aggregate_iterators_with_progress
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field

import cli

from backup import backup
from backup.context import context
from backup.context.action import Action
from backup.models import Changes, Path
from backup.utils import exporter

from . import cache
from ..utils.itertools import aggregate_iterators_with_progress


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

    def status(self) -> None:
        for status in list(self.generate_statuses()):
            status.print()

    def generate_statuses(self) -> Iterator[Changes]:
        combined_changes = self.scan_changes(quiet=True)
        for item, changes in zip(context.backup_config, combined_changes):
            yield (
                backup.Backup(
                    source=item.source,
                    dest=item.dest,
                    sub_check_path=self.sub_check_path,
                    paths=changes.paths,
                ).capture_status()
                if changes.paths
                else Changes()
            )

    def run_push(self, *, reverse: bool = False) -> None:
        any_include = any(rule.startswith("+") for rule in self.filter_rules)
        paths = self.paths
        if not paths and not any_include:
            paths = self.check_changed_paths(reverse=reverse)
        if paths:
            self.start_push(paths, reverse=reverse)

    def start_push(
        self,
        paths: list[list[Path]],
        *,
        reverse: bool = False,
    ) -> subprocess.CompletedProcess[str] | None:
        for config, paths_ in zip(context.backup_config, paths):
            if paths_:
                print(config.source)
                print(config.dest)
                print(paths_)
                backup.Backup(
                    source=config.source,
                    dest=context.extract_backup_dest() / config.dest,
                    paths=paths_,
                    sub_check_path=self.sub_check_path,
                ).push(reverse=reverse)
                cache.Backup(
                    source=config.source,
                    dest=context.extract_cache_path() / config.dest,
                    paths=paths_,
                    sub_check_path=self.sub_check_path,
                ).push()

    def check_changed_paths(self, *, reverse: bool) -> list[list[Path]]:
        changes: list[Changes] = list(self.scan_changes(reverse=reverse))
        remove_changes = (
            any(change for change in changes)
            and context.options.confirm_push
            and sys.stdin.isatty()
            and not self.ask_confirm(changes, reverse=reverse)
        )
        if remove_changes:
            changes = []  # pragma: nocover

        return [
            [
                change.source.relative_to(config.source) / change.path
                if change.source
                else change.path
                for change in changes_.changes
            ]
            for config, changes_ in zip(context.backup_config, changes)
        ]

    @classmethod
    def ask_confirm(cls, changes: list[Changes], *, reverse: bool = False) -> bool:
        message = "Pull?" if reverse else "Push?"
        cli.console.rule("Backup")
        for change in changes:
            change.print_structure.print(show_diff=context.options.show_file_diffs)
        response = cli.confirm(message, default=True)
        if not response and not context.options.show_file_diffs:
            for change in changes:
                change.print_structure.print(show_diff=context.options.show_file_diffs)
            response = cli.confirm(message, default=True)
        return response

    def scan_changes(
        self, *, quiet: bool = False, reverse: bool = False
    ) -> Iterator[Changes]:
        backups = [
            cache.Backup(
                source=item.source,
                dest=context.extract_cache_path() / item.dest,
                quiet=quiet,
                sub_check_path=self.sub_check_path,
                rules=item.rules.rules,
            )
            for item in context.backup_config
        ]
        entries = aggregate_iterators_with_progress(
            (backup_.generate_entries() for backup_ in backups),
            description="Checking",
            unit="Files",
        )
        for backup_, entries_ in zip(backups, entries):
            backup_.entries = set(entries_)
            yield backup_.status(reverse=reverse)

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
