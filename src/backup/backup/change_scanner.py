import sys
from collections.abc import Iterator
from dataclasses import dataclass

import cli

from backup.context import context
from backup.models import BackupConfig, Changes, PrintStructure
from backup.utils.itertools import aggregate_iterators_with_progress

from .cache import CacheScanner


@dataclass
class ChangeScanner:
    backup_configs: list[BackupConfig]

    def check_changes(self, *, reverse: bool) -> list[Changes]:
        batches = list(self.calculate_changes(reverse=reverse))
        remove_changes = (
            any(batches)
            and context.options.confirm_push
            and sys.stdin.isatty()
            and not self.ask_confirm(batches, reverse=reverse)
            and not self.ask_confirm(batches, reverse=reverse, show_diff=True)
        )
        return [[] for _ in self.backup_configs] if remove_changes else batches

    def calculate_changes(self, *, reverse: bool = False) -> Iterator[Changes]:
        scanners = [CacheScanner(backup) for backup in self.backup_configs]
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
        batches: list[Changes],
        *,
        reverse: bool = False,
        show_diff: bool = False,
    ) -> bool:
        message = "Pull?" if reverse else "Push?"
        if not show_diff:
            cli.console.rule("Backup")
        for changes in batches:
            PrintStructure.from_changes(changes).print(show_diff=show_diff)
        return cli.confirm(message, default=True)
