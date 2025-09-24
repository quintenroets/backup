import sys
from collections.abc import Iterator
from dataclasses import dataclass

import cli

from backup.context import context
from backup.models import BackupConfig, Changes
from backup.utils.itertools import aggregate_iterators_with_progress

from .cache import CacheScanner


@dataclass
class ChangeScanner:
    backup_configs: list[BackupConfig]

    def check_changes(self, *, reverse: bool) -> list[Changes]:
        changes: list[Changes] = list(self.calculate_changes(reverse=reverse))
        remove_changes = (
            any(change for change in changes)
            and context.options.confirm_push
            and sys.stdin.isatty()
            and not self.ask_confirm(changes, reverse=reverse)
            and not context.options.show_file_diffs
            and not self.ask_confirm(changes, reverse=reverse, show_diff=True)
        )
        return [] if remove_changes else changes

    def calculate_changes(
        self,
        *,
        quiet: bool = False,
        reverse: bool = False,
    ) -> Iterator[Changes]:
        scanners = [CacheScanner(backup, quiet=quiet) for backup in self.backup_configs]
        entries = aggregate_iterators_with_progress(
            (scanner.generate_entries() for scanner in scanners),
            description="Checking",
            unit="Files",
        )
        for scanner, entries_ in zip(scanners, entries, strict=True):
            scanner.entries = set(entries_)
            yield scanner.calculate_changes(reverse=reverse)

    @classmethod
    def ask_confirm(
        cls,
        changes: list[Changes],
        *,
        reverse: bool = False,
        show_diff: bool | None = None,
    ) -> bool:
        message = "Pull?" if reverse else "Push?"
        if show_diff is None:
            cli.console.rule("Backup")
            show_diff = context.options.show_file_diffs
        for change in changes:
            change.print_structure.print(show_diff=show_diff)
        return cli.confirm(message, default=True)
