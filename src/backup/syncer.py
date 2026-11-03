from __future__ import annotations

import json
import os
import re
from contextlib import suppress
from dataclasses import dataclass, field, replace
from datetime import datetime
from functools import cache
from stat import S_ISREG
from typing import TYPE_CHECKING, TypeVar

import cli
from package_utils.secrets_ import load_secret
from superpathlib import Path

if TYPE_CHECKING:
    import subprocess  # pragma: nocover
    from collections.abc import Callable, Iterable, Iterator  # pragma: nocover

T = TypeVar("T")


@dataclass
class PathRule:
    path: Path
    include: bool

    @property
    def depth(self) -> int:
        return len(self.path.parts)

    @classmethod
    def select(cls, paths: Iterable[str | Path]) -> list[PathRule]:
        return [cls(Path(path), include=True) for path in paths]


@dataclass(frozen=True)
class FileState:
    mtime: float = 0.0
    size: int = 0

    @classmethod
    def observe(cls, path: str | Path) -> FileState | None:
        """The state of the regular file at a path, or nothing to back up there."""
        state = None
        with suppress(FileNotFoundError, NotADirectoryError):
            stat = os.lstat(path)
            if S_ISREG(stat.st_mode):
                state = cls(stat.st_mtime, stat.st_size)
        return state


Snapshot = dict[str, FileState]


@dataclass
class RcloneConfig:
    overwrite_newer: bool = True
    retries: int = 5
    n_checkers: int = 100
    n_parallel_transfers: int = 100
    retries_sleep: str = "30s"
    order_by: str = "size,desc"
    drive_import_formats: str = "docx, xlsx"


@dataclass
class Syncer:
    source: Path
    dest: Path
    rules: list[PathRule] = field(default_factory=lambda: PathRule.select([""]))
    rclone: RcloneConfig = field(default_factory=RcloneConfig)

    @property
    def reversed(self) -> Syncer:
        return replace(self, source=self.dest, dest=self.source)

    def push(self) -> subprocess.CompletedProcess[str]:
        return self.transfer(cli.run, "sync", *self.generate_sync_options())

    def capture_push(self) -> str:
        return self.transfer(cli.capture_output, "sync", *self.generate_sync_options())

    def capture_pull(self) -> str:
        return self.reversed.capture_push()

    def delete(self) -> subprocess.CompletedProcess[str]:
        return self.execute(cli.run, "delete", self.dest, "--rmdirs")

    def export_files(self, export_format: str) -> str:
        formats = {"drive-export-formats": export_format}
        return self.reversed.transfer(cli.capture_output, "copy", formats)

    def list_remote_files(self) -> Snapshot:
        output = self.capture_output("lsjson", "-R", "--files-only", self.dest)
        return {
            info["Path"]: FileState(parse_modified_time(info["ModTime"]), info["Size"])
            for info in json.loads(output)
        }

    def capture_output(self, *args: object) -> str:
        return self.execute(cli.capture_output, *args)

    def transfer(self, function: Callable[..., T], verb: str, *args: object) -> T:
        return self.execute(function, verb, self.source, self.dest, *args)

    def execute(self, function: Callable[..., T], *args: object) -> T:
        sudo = ("sudo", "-E") if requires_root(self.dest) else ()
        with Path.tempfile() as filters:
            filters.lines = generate_filters(self.rules)
            options = ("--filter-from", filters, *self.generate_options())
            return function(*sudo, "rclone", *args, *options, env=load_rclone_env())

    def generate_sync_options(self) -> Iterator[object]:
        yield from ("--create-empty-src-dirs", "--progress")
        if requires_root(self.dest):
            yield "--no-update-dir-modtime"

    def generate_options(self) -> Iterator[object]:
        yield "--skip-links"
        if not self.rclone.overwrite_newer:
            yield "--update"
        yield {
            "retries": self.rclone.retries,
            "retries-sleep": self.rclone.retries_sleep,
            "order-by": self.rclone.order_by,
            "drive-import-formats": self.rclone.drive_import_formats,
            "checkers": self.rclone.n_checkers,
            "transfers": self.rclone.n_parallel_transfers,
        }


def create_syncer(path: Path) -> Syncer:
    is_home = path.is_relative_to(Path.HOME)
    remote = Path(resolve_remote())
    source = Path.HOME if is_home else Path("/")
    dest = remote / "home" if is_home else remote
    return Syncer(source, dest, PathRule.select([path.relative_to(source)]))


@cache
def resolve_remote() -> str:
    return cli.capture_output_lines("rclone listremotes", env=load_rclone_env())[0]


@cache
def load_rclone_env() -> dict[str, str]:
    env = dict(os.environ)
    if env.pop("RCLONE_PASSWORD_COMMAND", None) is not None:
        env["RCLONE_CONFIG_PASS"] = load_secret("rclone")
    return env


def requires_root(path: Path) -> bool:
    existing = (parent for parent in (path, *path.parents) if parent.exists())
    return ":" not in path.parts[0] and not os.access(next(existing), os.W_OK)


def parse_modified_time(value: str) -> float:
    return datetime.fromisoformat(value).timestamp()


def generate_filters(rules: list[PathRule]) -> Iterator[str]:
    for rule in rules:
        sign = "+" if rule.include else "-"
        if rule.depth:
            path = re.sub(r"[\\\[\]*?{}]", r"\\\g<0>", str(rule.path))
            yield f"{sign} /{path}"
            yield f"{sign} /{path}/**"
        else:
            yield f"{sign} /**"
    yield "- *"
