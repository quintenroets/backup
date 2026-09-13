import os
from collections.abc import Iterable, Iterator
from contextlib import suppress
from dataclasses import dataclass, field
from functools import cached_property

import cli

from backup.backup.models import Action, BackupConfig, Change, Path, Scope
from backup.backup.transfer_plan import TransferPlan
from backup.syncer import FileState

from .change_calculation import calculate_change, generate_unobserved_records


def scan_sources(backup_configs: list[BackupConfig], total: int) -> list[TransferPlan]:
    scanners = [SourceScanner(config) for config in backup_configs]
    scanned = cli.track_progress(
        generate_scanned_changes(scanners),
        description="Checking",
        unit="Files",
        total=total,
        cleanup_after_finish=True,
    )
    for scanner, change in scanned:
        if change is not None:
            scanner.changes.append(change)
    return [
        TransferPlan.from_changes(one.backup_config, one.changes, Action.push)
        for one in scanners
    ]


def generate_scanned_changes(
    scanners: list["SourceScanner"],
) -> Iterator[tuple["SourceScanner", Change | None]]:
    for scanner in scanners:
        for change in scanner.generate_changes():
            yield scanner, change


@dataclass
class SourceScanner:
    backup_config: BackupConfig
    changes: list[Change] = field(default_factory=list)
    walked_directories: set[str] = field(default_factory=set)
    scanned: set[str] = field(default_factory=set)

    @cached_property
    def source(self) -> str:
        return str(self.backup_config.source)

    @property
    def scope(self) -> Scope:
        return self.backup_config.scope

    def generate_changes(self) -> Iterator[Change | None]:
        for relative in self.generate_unscanned(self.generate_disk_paths()):
            yield self.calculate_change(relative, self.observe(relative))
        records = self.backup_config.sync_state
        for relative in generate_unobserved_records(records, self.scope, self.scanned):
            yield self.calculate_change(relative, self.observe_recorded(relative))

    def generate_disk_paths(self) -> Iterator[str]:
        for rule in self.scope.rules:
            if rule.include:
                base = str(rule.path) if rule.path.parts else ""
                source = self.backup_config.source / rule.path
                if self.scope.covers_child(base, name=source.name):
                    yield from self.scan_root(source, base)

    def scan_root(self, source: Path, base: str) -> Iterator[str]:
        if source.is_file():
            yield base
        else:
            yield from self.scan_directory(source, base)

    def scan_directory(self, source: Path, base: str) -> Iterator[str]:
        if source.exists() and not source.is_symlink():
            yield from self.walk(str(source), base)

    def walk(self, directory: str, base: str) -> Iterator[str]:
        if directory not in self.walked_directories:
            self.walked_directories.add(directory)
            with suppress(PermissionError), os.scandir(directory) as entries:
                for entry in entries:
                    yield from self.scan_entry(entry, base)

    def scan_entry(self, entry: os.DirEntry[str], base: str) -> Iterator[str]:
        if not entry.is_symlink():
            relative = f"{base}/{entry.name}" if base else entry.name
            if self.scope.covers_child(relative, name=entry.name):
                if entry.is_dir(follow_symlinks=False):
                    yield from self.walk(entry.path, relative)
                else:
                    yield relative

    def calculate_change(
        self,
        relative: str,
        observed: FileState | None,
    ) -> Change | None:
        records = self.backup_config.sync_state
        oversized = observed is not None and self.scope.exceeds_size_limit(
            relative,
            observed,
        )
        return (
            None
            if oversized
            else calculate_change(records, relative, observed, Action.push)
        )

    def observe(self, relative: str) -> FileState | None:
        return FileState.observe(self.absolute(relative))

    def observe_recorded(self, relative: str) -> FileState | None:
        """Nothing to observe for an ignored path, which reads as a deletion."""
        return None if self.scope.ignored(relative) else self.observe(relative)

    def generate_unscanned(self, paths: Iterable[str]) -> Iterator[str]:
        for relative in paths:
            if relative not in self.scanned:
                self.scanned.add(relative)
                yield relative

    def absolute(self, relative: str) -> str:
        return f"{self.source}/{relative}" if relative else self.source
