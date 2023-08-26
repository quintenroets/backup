from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

import cli

from .path import Path


class ChangeType(Enum):
    created = "created"
    modified = "modified"
    deleted = "deleted"
    preserved = "preserved"

    @classmethod
    @property
    def symbol_mapper(cls):
        return {
            "+": ChangeType.created,
            "*": ChangeType.modified,
            "-": ChangeType.deleted,
            "=": ChangeType.preserved,
        }

    @classmethod
    @property
    def color_mapper(cls):
        return {"+": "green", "*": "blue", "-": "red"}

    @classmethod
    @property
    def reverse_symbol_mapper(cls):
        return {v: k for k, v in cls.symbol_mapper.items()}

    @classmethod
    def from_symbol(cls, symbol: str):
        return cls.symbol_mapper[symbol]

    @property
    def color(self):
        return self.color_mapper[self.symbol]

    @property
    def symbol(self):
        return self.reverse_symbol_mapper[self]

    def __str__(self):
        return self.symbol

    @property
    def sort_order(self):
        symbols = list(self.symbol_mapper.keys())
        return symbols.index(self.symbol)

    def __lt__(self, other):
        return self.sort_order.__lt__(other.sort_order)


@dataclass
class Change:
    path: Path
    type: ChangeType

    @classmethod
    def from_pattern(cls, pattern: str):
        type_ = ChangeType.from_symbol(pattern[0])
        path = Path(pattern[2:])
        return Change(path, type_)

    @property
    def message(self):
        return f"{self.type} [bold {self.type.color}]{self.path}\n"

    @property
    def sort_index(self):
        return self.type, self.path

    @property
    def skip_print(self):
        return (Path.HOME / self.path).is_relative_to(Path.hashes)

    def print(self):
        cli.console.print(self.message, end="")


@dataclass
class PrintChange:
    path: Path
    type: ChangeType | None
    indent_count: int = 0

    @property
    def root(self):
        return self.path.parts[0]

    @property
    def path_from_root(self):
        return self.path.relative_to(self.root)

    @property
    def child(self):
        return PrintChange(self.path_from_root, self.type, self.indent_count + 1)

    def __hash__(self):
        attributes = tuple(asdict(self).values())
        return hash(attributes)

    def print(self):
        whitespace = "  " * self.indent_count
        symbol = self.type.symbol if self.type else "\u2022"
        color = self.type.color if self.type else "black"

        message = str(self.path)
        home_path_str = str(Path.HOME.relative_to(Path("/")))
        message = message.replace(home_path_str, "HOME")
        available_width = cli.console.width - len(whitespace + symbol + " " + "-")
        message_chunks = [
            message[start : start + available_width]
            for start in range(0, len(message), available_width)
        ]
        for i, message in enumerate(message_chunks):
            prefix = f"{symbol} " if i == 0 else "  "
            need_suffix = i + 1 < len(message_chunks) and " " not in (
                message[-1],
                message_chunks[i + 1][0],
            )
            suffix = "-" if need_suffix else ""
            formatted_message = f"{whitespace}{prefix}[bold {color}]{message}{suffix}"
            cli.console.print(formatted_message)


@dataclass
class PrintStructure:
    root: PrintChange | None
    changes: list[PrintChange]
    substructures: list[PrintStructure]

    @classmethod
    def from_changes(cls, changes: list[Change]):
        print_changes = [
            PrintChange(change.path, change.type)
            for change in changes
            if not change.skip_print
        ]
        return cls.from_print_changes(print_changes)

    def un_indent(self):
        if self.root is not None:
            self.root.indent_count -= 1
        for c in self.changes:
            c.indent_count -= 1
        for substructure in self.substructures:
            substructure.un_indent()

    def closest_nodes(self):
        closest = (
            0
            if self.changes
            else 1 + min(sub.closest_nodes() for sub in self.substructures)
        )
        return closest

    def current_level_empty(self):
        return not self.changes and len(self.substructures) == 1

    @classmethod
    def from_print_changes(cls, changes: list[PrintChange]):
        changes_per_root = {}
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
                root_path = Path(root_name)
                children = [c.child for c in sub_print_changes]
                sub_structure = PrintStructure.from_print_changes(children)

                if sub_structure.current_level_empty():
                    if sub_structure.root is None:
                        sub_structure.root = sub_structure.substructures[0].root

                    root_path /= sub_structure.root.path
                    sub_structure = sub_structure.substructures[0]
                    sub_structure.un_indent()

                sub_structure.root = PrintChange(
                    root_path, None, sub_print_changes[0].indent_count
                )
                substructures.append(sub_structure)

        return PrintStructure(None, changes, substructures)

    def print(self):
        if self.root is not None:
            self.root.print()
        for change in self.changes:
            change.print()
        substructures = sorted(self.substructures, key=lambda s: s.closest_nodes())
        for sub_structure in substructures:
            sub_structure.print()


@dataclass
class Changes:
    changes: list[Change] = field(default_factory=list)

    def __post_init__(self):
        self.changes = sorted(self.changes, key=lambda c: c.sort_index)

    def __iter__(self):
        yield from self.changes

    def __bool__(self):
        return bool(self.changes)

    @property
    def paths(self):
        return [change.path for change in self.changes]

    @classmethod
    def from_patterns(cls, patterns: list[str]):
        return Changes([Change.from_pattern(pattern) for pattern in patterns])

    def print(self):
        print_structure = PrintStructure.from_changes(self.changes)
        print_structure.print()
        print("")

    def print_paths(self, paths, indent=0):
        parts_mapper = {}
        for p in paths:
            parts_mapper[p.parts[0]] = parts_mapper.get(p.parts[0], []) + [
                p.relative_to(p.parts[0])
            ]

        for name, paths in parts_mapper.items():
            tab = indent * " "
            if len(paths) == 1:
                print(f"{tab}+ {name}/{paths[0]}")
            else:
                print(f"{tab}{name}: ")
                self.print_paths(paths, indent + 1)
