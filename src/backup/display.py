from __future__ import annotations

import difflib
import io
from itertools import pairwise
from os.path import commonpath
from typing import TYPE_CHECKING

import cli
from rich.table import Column, Table
from rich.text import Text
from rich.tree import Tree
from superpathlib import Path

from .syncer import Syncer

if TYPE_CHECKING:
    from .models import Plan

colors = {"+": "green", "*": "blue", "-": "red", "•": "dim"}


def print_changes(plan: Plan, *, show_diff: bool, reverse: bool) -> None:
    backup, changes = plan
    shown = dict(sorted(changes.items())[:1000])
    parents = [path.parent for path in shown]
    common = Path(commonpath(parents))
    root = backup.source / common
    is_home = root.is_relative_to(Path.HOME)
    tree = Tree(Text(str("HOME" / root.relative_to(Path.HOME) if is_home else root)))
    directories = {Path(commonpath(pair)) for pair in pairwise(parents)} - {common}
    nodes = {common: tree}
    for path, symbol in sorted((shown | dict.fromkeys(directories, "•")).items()):
        ancestor = next(directory for directory in path.parents if directory in nodes)
        label = Table.grid(Column(), Column(overflow="fold"), padding=(0, 1))
        name = Text(str(path.relative_to(ancestor)))
        label.add_row(symbol, name, style=f"bold {colors[symbol]}")
        nodes[path] = nodes[ancestor].add(label)
    if show_diff:
        add_diffs((backup, shown), nodes, reverse=reverse)
    if hidden := len(changes) - len(shown):
        tree.add(f"… {hidden} more")
    cli.console.print(tree)


def add_diffs(plan: Plan, nodes: dict[Path, Tree], *, reverse: bool) -> None:
    backup, changes = plan
    on_remote = "+*" if reverse else "*-"
    with Path.tempdir(in_memory=False) as remote:
        if files := [path for path, symbol in changes.items() if symbol in on_remote]:
            syncer = Syncer(backup.dest, remote, backup.config.rclone)
            with cli.console.status("Loading remote content"):
                syncer.with_paths(files).run("copy")
        sides = (backup.source, remote) if reverse else (remote, backup.source)
        for path in changes:
            nodes[path].add(render_diff(*(side / path for side in sides)))


def render_diff(old: Path, new: Path) -> Text | str:
    read_limit = 64_000
    contents = []
    for file in (old, new):
        with file.open("rb") if file.is_file() else io.BytesIO() as stream:
            contents.append(stream.read(read_limit + 1))
    line_limit = 20
    binary = b"\0" in b"".join(contents)
    texts = (content.decode(errors="backslashreplace") for content in contents)
    old_lines, new_lines = ([] if binary else text.splitlines() for text in texts)
    lines = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))[2:]
    clipped = any(len(content) > read_limit for content in contents)
    shown = lines[:line_limit] + (["…"] if len(lines) > line_limit or clipped else [])
    diff = Text("\n").join(Text(line, colors.get(line[:1], "")) for line in shown)
    return "[dim]binary" if binary else diff if shown else "[dim]empty"
