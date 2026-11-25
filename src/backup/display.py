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

if TYPE_CHECKING:
    from .models import Plan

directory_symbol = "•"
colors = {"+": "green", "*": "blue", "-": "red", directory_symbol: "dim"}


def print_changes(plan: Plan, *, show_diff: bool, reverse: bool) -> None:
    backup, changes = plan
    sides = (backup.source, backup.cache) if reverse else (backup.cache, backup.source)
    shown = dict(sorted((change.path, change.type) for change in changes)[:1000])
    parents = [path.parent for path in shown]
    common = Path(commonpath(parents))
    root = backup.source / common
    is_home = root.is_relative_to(Path.HOME)
    tree = Tree(Text(str("HOME" / root.relative_to(Path.HOME) if is_home else root)))
    directories = {Path(commonpath(pair)) for pair in pairwise(parents)} - {common}
    symbols = shown | dict.fromkeys(directories, directory_symbol)
    nodes = {common: tree}
    for path, symbol in sorted(symbols.items()):
        ancestor = next(directory for directory in path.parents if directory in nodes)
        label = Table.grid(Column(), Column(overflow="fold"), padding=(0, 1))
        name = Text(str(path.relative_to(ancestor)))
        label.add_row(symbol, name, style=f"bold {colors[symbol]}")
        nodes[path] = nodes[ancestor].add(label)
        if show_diff and path not in directories:
            nodes[path].add(render_diff(*(side / path for side in sides)))
    if hidden := len(changes) - len(shown):
        tree.add(f"… {hidden} more")
    cli.console.print(tree)


def render_diff(old: Path, new: Path) -> Text | str:
    read_limit = 64_000
    contents = []
    for file in (old, new):
        with file.open("rb") if file.exists() else io.BytesIO() as stream:
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
