from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum

import cli

from . import differ
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
        return {"+": "green", "*": "blue", "-": "red", "=": "black"}

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
    source: Path = None
    dest: Path = None
    max_diff_lines_per_file: int = 20

    @classmethod
    def from_pattern(cls, pattern: str, source: Path = None, dest: Path = None):
        type_ = ChangeType.from_symbol(pattern[0])
        path = Path(pattern[2:])
        return Change(path, type_, source, dest)

    @property
    def message(self):
        return f"{self.type} [bold {self.type.color}]{self.path}\n"

    @property
    def sort_index(self):
        return self.type, self.path

    @property
    def skip_print(self):
        return (self.source / self.path).is_relative_to(Path.hashes)  # noqa

    def print(self):
        cli.console.print(self.message, end="")

    def get_diff_lines(self, color=True):
        return differ.get_diff(
            self.path,
            self.source,
            self.dest,
            color=color,
            max_lines=self.max_diff_lines_per_file,
        )


@dataclass
class PrintChange:
    path: Path
    change: Change | None = None
    indent_count: int = 0
    indent = "  "

    @property
    def root(self):
        return self.path.parts[0]

    @property
    def path_from_root(self):
        return self.path.relative_to(self.root)

    @property
    def child(self):
        return PrintChange(
            self.path_from_root,
            self.change,
            self.indent_count + 1,
        )

    def __hash__(self):
        attributes = tuple(asdict(self).values())
        return hash(attributes)

    def print(self, show_diff: bool = False):
        whitespace = self.indent * self.indent_count
        symbol = self.change.type.symbol if self.change else "\u2022"
        color = self.change.type.color if self.change else "black"

        full_path = self.change.source / self.path if self.change else None
        path = (
            Path("HOME") / full_path.relative_to(Path.HOME)
            if full_path and full_path.is_relative_to(Path.HOME)
            else self.path
        )
        message = str(path)
        available_width = cli.console.width - len(whitespace + symbol + " " + "-")
        message_chunks = [
            message[start : start + available_width]
            for start in range(0, len(message), available_width)
        ]
        last_chunk_index = len(message_chunks) - 1
        lines = []
        for i, message in enumerate(message_chunks):
            prefix = f"{symbol} " if i == 0 else "  "
            need_suffix = i < last_chunk_index and " " not in (
                message[-1],
                message_chunks[i + 1][0],
            )
            suffix = "-" if need_suffix else ""
            formatted_message = f"{whitespace}{prefix}[bold {color}]{message}{suffix}"
            lines.append(formatted_message)
        message = "\n".join(lines)
        cli.console.print(message)
        if show_diff and self.change:
            self.print_diff()

    def print_diff(self):
        if self.change.type == ChangeType.modified:
            diff_lines = self.change.get_diff_lines(color=False)
            lines = []
            for line in diff_lines:
                match line[0]:
                    case ChangeType.created.symbol:
                        change_type = ChangeType.created
                    case ChangeType.deleted.symbol:
                        change_type = ChangeType.deleted
                    case " ":
                        change_type = ChangeType.preserved
                    case _:
                        change_type = None

                if change_type is not None:
                    line = line[1:].strip()
                if change_type not in (ChangeType.preserved, None):
                    line = f"{change_type.symbol} {line}"
                if change_type is not None:
                    line = f"[{change_type.color}]{line}"
                lines.append(line)
        else:
            source = (
                self.change.source
                if self.change.type == ChangeType.created
                else self.change.dest
            )
            full_path = source / self.change.path
            try:
                lines = full_path.lines
            except UnicodeDecodeError:
                lines = []

        whitespace = self.indent * (self.indent_count + 1)
        available_width = cli.console.width - len(whitespace)
        for line in lines:
            chunks = [
                whitespace + line[start : start + available_width]
                for start in range(0, len(line), available_width)
            ]
            line_message = "\n".join(chunks)
            cli.console.print(line_message, highlight=False)


@dataclass
class PrintStructure:
    root: PrintChange | None
    changes: list[PrintChange]
    substructures: list[PrintStructure]
    max_show: int = 1000
    show_diff: bool = False

    @classmethod
    def from_changes(cls, changes: list[Change]):
        print_changes = [
            PrintChange(change.path, change)
            for change in changes[: cls.max_show]
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

    def print(self, show_diff: bool = False):
        if self.root is not None:
            self.root.print(show_diff=show_diff)
        for change in self.changes:
            change.print(show_diff=show_diff)
        substructures = sorted(self.substructures, key=lambda s: s.closest_nodes())
        for sub_structure in substructures:
            sub_structure.print(show_diff=show_diff)


@dataclass
class Changes:
    changes: list[Change] = field(default_factory=list)
    print_structure: PrintStructure = None

    def __post_init__(self):
        self.changes = sorted(self.changes, key=lambda c: c.sort_index)
        self.print_structure = PrintStructure.from_changes(self.changes)

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

    def ask_confirm(self, message: str, show_diff=False):
        self.print(title="Backup", show_diff=show_diff)
        message = "\n" + message
        return cli.confirm(message, default=True)

    def print(self, title=None, show_diff=False):
        if title is not None:
            cli.console.clear()
            cli.console.rule("Backup")
        self.print_structure.print(show_diff=show_diff)
