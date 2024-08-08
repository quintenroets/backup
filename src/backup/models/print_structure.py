from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from .change import Change
from .path import Path
from .print_change import PrintChange


@dataclass
class PrintStructure:
    root: PrintChange | None
    changes: list[PrintChange]
    substructures: list[PrintStructure]
    max_show: int = 1000
    show_diff: bool = False

    @classmethod
    def from_changes(cls, changes: list[Change]) -> PrintStructure:
        print_changes = [
            PrintChange(change.path, change)
            for change in changes[: cls.max_show]
            if not change.skip_print
        ]
        return cls.from_print_changes(print_changes)

    def un_indent(self) -> None:
        if self.root is not None:
            self.root.indent_count -= 1
        for c in self.changes:
            c.indent_count -= 1
        for substructure in self.substructures:
            substructure.un_indent()

    def closest_nodes(self) -> int:
        return (
            0
            if self.changes
            else 1 + min(sub.closest_nodes() for sub in self.substructures)
        )

    def current_level_empty(self) -> bool:
        return not self.changes and len(self.substructures) == 1

    @classmethod
    def from_print_changes(cls, changes: list[PrintChange]) -> PrintStructure:
        changes_per_root: dict[str, list[PrintChange]] = {}
        for change in changes:
            if change.root not in changes_per_root:
                changes_per_root[change.root] = []
            changes_per_root[change.root].append(change)

        substructures = []
        changes = []
        for root_name, sub_print_changes in changes_per_root.items():
            if len(sub_print_changes) == 1:
                changes += sub_print_changes
            else:
                sub_structure = cls.create_sub_structure(root_name, sub_print_changes)
                substructures.append(sub_structure)

        return PrintStructure(None, changes, substructures)

    @classmethod
    def create_sub_structure(
        cls,
        root_name: str,
        sub_print_changes: list[PrintChange],
    ) -> PrintStructure:
        root_path = Path(root_name)
        children = [c.child for c in sub_print_changes]
        sub_structure = PrintStructure.from_print_changes(children)

        if sub_structure.current_level_empty():
            if sub_structure.root is None:
                sub_structure.root = sub_structure.substructures[0].root
            root = cast(PrintChange, sub_structure.root)
            root_path /= root.path
            sub_structure = sub_structure.substructures[0]
            sub_structure.un_indent()

        sub_structure.root = PrintChange(
            root_path,
            Change(Path()),
            sub_print_changes[0].indent_count,
        )
        return sub_structure

    def print(self, *, show_diff: bool = False) -> None:
        if self.root is not None:
            self.root.print(show_diff=show_diff)
        for change in self.changes:
            change.print(show_diff=show_diff)
        substructures = sorted(self.substructures, key=lambda s: s.closest_nodes())
        for sub_structure in substructures:
            sub_structure.print(show_diff=show_diff)
