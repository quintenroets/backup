from __future__ import annotations

import difflib
import typing
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from itertools import islice

import cli

from .models import Action, Change, Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover

    from rich.console import RenderableType  # pragma: nocover
    from rich.table import Table  # pragma: nocover
    from rich.tree import Tree  # pragma: nocover

    from .context import Options  # pragma: nocover
    from .transfer_plan import TransferPlan  # pragma: nocover

cutoff_marker = "…"


def show_changes(plans: list[TransferPlan], options: Options) -> None:
    cli.console.rule("Backup")
    for plan in plans:
        with stage_diff(plan, options) as diff_roots:
            print_changes(plan, diff_roots)


def print_changes(plan: TransferPlan, diff_roots: DiffRoots | None) -> None:
    from rich.tree import Tree  # noqa: PLC0415

    max_shown = 1000
    root = ChangeTree()
    for change in sorted(plan.changes, key=sort_key)[:max_shown]:
        root.insert(change)
    tree = Tree(str(plan.config.source))
    root.render(tree, diff_roots)
    hidden = len(plan.changes) - max_shown
    if hidden > 0:
        tree.add(f"{cutoff_marker} {hidden} more")
    cli.console.print(tree)


@contextmanager
def stage_diff(plan: TransferPlan, options: Options) -> Iterator[DiffRoots | None]:
    if options.diff:
        with Path.tempdir() as staging:
            syncer = plan.config.create_syncer(plan.paths, Action.pull)
            with cli.console.status("Loading remote content"):
                replace(syncer, dest=staging).transfer(cli.run, "copy")
            local = plan.config.source
            pushing = options.action == Action.push
            yield DiffRoots(staging, local) if pushing else DiffRoots(local, staging)
    else:
        yield None


def sort_key(change: Change) -> tuple[int, list[str]]:
    return change.type.sort_order, change.path.split("/")


@dataclass
class DiffRoots:
    old: Path
    new: Path


@dataclass
class ChangeTree:
    path: Path = field(default_factory=Path)
    change: Change | None = None
    children: dict[str, ChangeTree] = field(default_factory=dict)

    def insert(self, change: Change) -> None:
        node = self
        for part in change.path.split("/"):
            node = node.children.setdefault(part, ChangeTree(Path(part)))
        node.change = change

    def render(self, tree: Tree, diff_roots: DiffRoots | None) -> None:
        if self.change is not None and diff_roots is not None:
            tree.add(render_diff(self.change.path, diff_roots))
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
        distances = (1 + child.collapsed.distance_to_leaf for child in children)
        return min(distances, default=0)

    @property
    def label(self) -> Table:
        from rich.table import Column, Table  # noqa: PLC0415

        style = f"bold {self.color}"
        columns = (Column(style=style), Column(style=style, overflow="fold"))
        grid = Table.grid(*columns, padding=(0, 1))
        grid.add_row(self.symbol, self.description)
        return grid

    @property
    def description(self) -> str:
        conflicted = self.change is not None and self.change.conflict
        suffix = " [yellow](modified locally)" if conflicted else ""
        return f"{self.path}{suffix}"

    @property
    def symbol(self) -> str:
        return "•" if self.change is None else self.change.type.symbol

    @property
    def color(self) -> str:
        return "black" if self.change is None else self.change.type.color


def render_diff(path: str, roots: DiffRoots) -> RenderableType:
    from rich.syntax import Syntax  # noqa: PLC0415

    old = read_lines(roots.old / path)
    new = read_lines(roots.new / path)
    diff = None if old is None or new is None else calculate_diff(old, new)
    return (
        "[black]binary content"
        if diff is None
        else Syntax(diff, "diff", background_color="default", word_wrap=True)
        if diff
        else "[black]identical content"
    )


def calculate_diff(old: list[str], new: list[str]) -> str:
    diff = islice(difflib.unified_diff(old, new, lineterm=""), 2, None)
    return "\n".join(limit_diff_lines(diff))


def limit_diff_lines(diff: Iterator[str]) -> Iterator[str]:
    max_lines = 20
    yield from islice(diff, max_lines)
    if next(diff, None) is not None:
        yield cutoff_marker


def read_lines(path: Path) -> list[str] | None:
    content = path.byte_content if path.exists() else b""
    return None if b"\0" in content else content.decode(errors="replace").splitlines()
