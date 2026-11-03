import os
from collections.abc import Iterator
from dataclasses import dataclass, field, replace

import cli

from .models import BackupConfig, Change, ChangeType, Scope
from .syncer import FileState, Snapshot
from .transfer_plan import TransferPlan


def scan_sources(configs: list[BackupConfig]) -> list[TransferPlan]:
    scanners = [SourceScanner(config) for config in configs]
    total = sum(len(config.records) for config in configs)
    paths = (relative for scanner in scanners for relative in scanner.observe())
    for _ in cli.track_progress(paths, "Checking", "Files", total):
        pass
    return [scanner.create_plan() for scanner in scanners]


@dataclass
class SourceScanner:
    config: BackupConfig
    observed: Snapshot = field(default_factory=dict)

    @property
    def scope(self) -> Scope:
        return self.config.scope

    def create_plan(self) -> TransferPlan:
        detected = detect_changes(self.observed, self.config.records.local, self.scope)
        kept = [change for change in detected if not self.oversized(change.path)]
        return TransferPlan(self.config, kept)

    def oversized(self, relative: str) -> bool:
        state = self.observed.get(relative)
        return state is not None and self.scope.exceeds_size_limit(relative, state)

    def observe(self) -> Iterator[str]:
        for relative, absolute in self.generate_disk_paths():
            state = FileState.observe(absolute)
            if state is not None:
                self.observed[relative] = state
                yield relative

    def generate_disk_paths(self) -> Iterator[tuple[str, str]]:
        for rule in self.scope.deepest_first:
            base = str(rule.path) if rule.depth else ""
            if rule.include and not self.scope.ignored(base):
                source = self.config.source / rule.path
                if source.is_dir():
                    yield from self.walk(str(source), base)
                else:
                    yield base, str(source)

    def walk(self, directory: str, base: str) -> Iterator[tuple[str, str]]:
        with os.scandir(directory) as entries:
            for entry in entries:
                relative = f"{base}/{entry.name}" if base else entry.name
                if self.scope.continues_walk(relative, name=entry.name):
                    if entry.is_dir(follow_symlinks=False):
                        yield from self.walk(entry.path, relative)
                    else:
                        yield relative, entry.path


def scan_remote(config: BackupConfig) -> TransferPlan:
    remote_path = str(config.dest).split(":")[-1]
    with cli.console.status(f"Reading remote filesystem at {remote_path}"):
        remote_files = config.list_remote()
    return TransferPlan(config, detect_pull_changes(config, remote_files))


def detect_pull_changes(config: BackupConfig, remote_files: Snapshot) -> list[Change]:
    detected = detect_changes(remote_files, config.records.remote, config.scope)
    kept = [change for change in detected if not config.scope.ignored(change.path)]
    local = config.observe_local(change.path for change in kept)
    modified = detect_modifications(local, config.records.local)
    conflicts = {change.path for change in modified}
    return [replace(change, conflict=change.path in conflicts) for change in kept]


def detect_changes(
    observed: Snapshot,
    recorded: Snapshot,
    scope: Scope,
) -> Iterator[Change]:
    """What it takes to bring the recorded snapshot in line with the observed one."""
    yield from detect_modifications(observed, recorded)
    for relative in recorded.keys() - observed:
        if scope.includes(relative):
            yield Change(relative, ChangeType.deleted)


def detect_modifications(observed: Snapshot, recorded: Snapshot) -> Iterator[Change]:
    for relative, state in observed.items():
        previous = recorded.get(relative)
        if state != previous:
            type_ = ChangeType.created if previous is None else ChangeType.modified
            yield Change(relative, type_)
