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

from .models import ChangeType

if TYPE_CHECKING:
    from .models import Plan

colors: dict[str | None, str] = {
    ChangeType.created: "green",
    ChangeType.modified: "blue",
    ChangeType.deleted: "red",
    None: "dim",
}


def print_changes(plan: Plan, *, show_diff: bool, reverse: bool) -> None:
    config, changes = plan
    sides = (config.source, config.cache) if reverse else (config.cache, config.source)
    types = dict(sorted((change.path, change.type) for change in changes)[:1000])
    parents = [path.parent for path in types]
    common = Path(commonpath(parents))
    root = config.source / common
    is_home = root.is_relative_to(Path.HOME)
    tree = Tree(Text(str("HOME" / root.relative_to(Path.HOME) if is_home else root)))
    directories = {Path(commonpath(pair)) for pair in pairwise(parents)} - {common}
    labels = types | dict.fromkeys(directories)
    nodes = {common: tree}
    for path, type_ in sorted(labels.items()):
        anchor = next(directory for directory in path.parents if directory in nodes)
        label = Table.grid(Column(), Column(overflow="fold"), padding=(0, 1))
        name = Text(str(path.relative_to(anchor)))
        label.add_row(type_ or "•", name, style=f"bold {colors[type_]}")
        nodes[path] = nodes[anchor].add(label)
        if show_diff and type_:
            nodes[path].add(render_diff(*(side / path for side in sides)))
    if hidden := len(changes) - len(types):
        tree.add(f"… {hidden} more")
    cli.console.print(tree)


def render_diff(old: Path, new: Path) -> Text | str:
    read_limit = 64_000
    contents = []
    for file in (old, new):
        with file.open("rb") if file.exists() else io.BytesIO() as stream:
            contents.append(stream.read(read_limit + 1))
    max_lines = 20
    binary = b"\0" in b"".join(contents)
    texts = (content.decode(errors="backslashreplace") for content in contents)
    old_lines, new_lines = ([] if binary else text.splitlines() for text in texts)
    lines = list(difflib.unified_diff(old_lines, new_lines, lineterm=""))[2:]
    clipped = any(len(content) > read_limit for content in contents)
    shown = lines[:max_lines] + (["…"] if len(lines) > max_lines or clipped else [])
    diff = Text("\n").join(Text(line, colors.get(line[:1], "")) for line in shown)
    return "[dim]binary" if binary else diff if shown else "[dim]empty"
