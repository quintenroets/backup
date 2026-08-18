from __future__ import annotations

import difflib
import typing
from dataclasses import dataclass, field, replace
from itertools import islice

import cli

from .models import Change, Changes, Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover

    from rich.console import RenderableType  # pragma: nocover
    from rich.table import Table  # pragma: nocover
    from rich.tree import Tree  # pragma: nocover

max_changes_shown = 1000
max_diff_lines_per_file = 20
cutoff_marker = "…"
annotation_color = "black"
binary_message = "binary content"
identical_message = "identical content"


@dataclass
class DiffRoots:
    source: Path
    staging: Path


@dataclass
class ChangeTree:
    path: Path = field(default_factory=Path)
    change: Change | None = None
    children: dict[str, ChangeTree] = field(default_factory=dict)
    hidden_changes: int = 0

    @classmethod
    def from_changes(cls, changes: Changes) -> ChangeTree:
        root = cls(hidden_changes=max(len(changes) - max_changes_shown, 0))
        for change in islice(changes, max_changes_shown):
            root.insert(change)
        return root

    def insert(self, change: Change) -> None:
        node = self
        for part in change.path.parts:
            node = node.children.setdefault(part, ChangeTree(Path(part)))
        node.change = change

    def print(self, diff_roots: DiffRoots | None) -> None:
        from rich.tree import Tree

        tree = Tree("", hide_root=True)
        self.render(tree, diff_roots)
        if self.hidden_changes:
            tree.add(f"{cutoff_marker} {self.hidden_changes} more")
        cli.console.print(tree)

    def render(self, tree: Tree, diff_roots: DiffRoots | None) -> None:
        if self.change is not None and diff_roots is not None:
            tree.add(create_diff_content(self.change.path, diff_roots))
        for child in self.ordered_children:
            child.render(tree.add(child.label), diff_roots)

    @property
    def ordered_children(self) -> list[ChangeTree]:
        children = [child.collapsed for child in self.children.values()]
        return sorted(children, key=lambda child: child.distance_to_leaf)

    @property
    def collapsed(self) -> ChangeTree:
        node = self
        while node.change is None and len(node.children) == 1:
            (only_child,) = node.children.values()
            node = replace(only_child, path=node.path / only_child.path)
        return node

    @property
    def distance_to_leaf(self) -> int:
        children = self.children.values()
        distances = [child.collapsed.distance_to_leaf for child in children]
        return 1 + min(distances) if distances else 0

    @property
    def label(self) -> Table:
        from rich.table import Column, Table

        style = f"bold {self.color}"
        columns = (Column(style=style), Column(style=style, overflow="fold"))
        grid = Table.grid(*columns, padding=(0, 1))
        grid.add_row(self.symbol, self.description)
        return grid

    @property
    def description(self) -> str:
        conflicted = self.change is not None and self.change.conflict
        suffix = " [yellow](modified locally)" if conflicted else ""
        return f"{self.path_message}{suffix}"

    @property
    def symbol(self) -> str:
        return "•" if self.change is None else self.change.type.symbol

    @property
    def color(self) -> str:
        return "black" if self.change is None else self.change.type.color

    @property
    def path_message(self) -> str:
        relative_home = Path.HOME.relative_to("/")
        path = (
            Path("HOME") / self.path.relative_to(relative_home)
            if self.path.is_relative_to(relative_home)
            else self.path
        )
        return str(path)


def create_diff_content(path: Path, roots: DiffRoots) -> RenderableType:
    from rich.syntax import Syntax

    remote = FileContent.read(roots.staging / path)
    local = FileContent.read(roots.source / path)
    binary = remote.binary or local.binary
    diff = "" if binary else calculate_diff(remote.lines, local.lines)
    message = binary_message if binary else identical_message
    return (
        Syntax(diff, "diff", background_color="default", word_wrap=True)
        if diff
        else f"[{annotation_color}]{message}"
    )


def calculate_diff(remote: list[str], local: list[str]) -> str:
    diff = islice(difflib.unified_diff(remote, local, lineterm=""), 2, None)
    return "\n".join(limit_diff_lines(diff))


def limit_diff_lines(diff: Iterator[str]) -> Iterator[str]:
    yield from islice(diff, max_diff_lines_per_file)
    if next(diff, None) is not None:
        yield cutoff_marker


@dataclass
class FileContent:
    lines: list[str]
    binary: bool

    @classmethod
    def read(cls, path: Path) -> FileContent:
        content = path.byte_content if path.exists() else b""
        binary = b"\0" in content
        lines = [] if binary else content.decode(errors="replace").splitlines()
        return cls(lines, binary)
