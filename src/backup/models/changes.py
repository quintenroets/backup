from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict, dataclass, field
from typing import cast

import cli

from .change import Change, ChangeType
from .path import Path


@dataclass
class PrintChange:
    path: Path
    change: Change
    indent_count: int = 0
    indent = "  "

    @property
    def root(self) -> str:
        return self.path.parts[0]

    @property
    def path_from_root(self) -> Path:
        return self.path.relative_to(self.root)

    @property
    def child(self) -> PrintChange:
        return PrintChange(
            self.path_from_root,
            self.change,
            self.indent_count + 1,
        )

    def __hash__(self) -> int:
        attributes = tuple(asdict(self).values())
        return hash(attributes)

    def print(self, show_diff: bool = False) -> None:
        whitespace = self.indent * self.indent_count
        symbol = self.change.type.symbol if self.change else "\u2022"
        color = self.change.type.color if self.change.path.parts else "black"

        root = Path("/")
        relative_home = Path.HOME.relative_to(root)
        path = (
            Path("HOME") / self.path.relative_to(relative_home)
            if self.path.is_relative_to(relative_home)
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
        if show_diff and self.change.path.parts:
            self.print_diff()

    def print_diff(self) -> None:
        lines = self.generate_print_lines()
        whitespace = self.indent * (self.indent_count + 1)
        available_width = cli.console.width - len(whitespace)
        for line in lines:
            chunks = [
                whitespace + line[start : start + available_width]
                for start in range(0, len(line), available_width)
            ]
            line_message = "\n".join(chunks)
            cli.console.print(line_message, highlight=False)

    def generate_print_lines(self) -> Iterator[str]:
        return (
            self.generate_diff_lines()
            if self.change.type == ChangeType.modified
            else self.generate_path_lines()
        )

    def generate_diff_lines(self) -> Iterator[str]:
        diff_lines = self.change.get_diff_lines(color=False)
        for line in diff_lines:
            change_type: ChangeType | None
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
                if change_type != ChangeType.preserved:
                    line = f"{change_type.symbol} {line}"
                yield f"[{change_type.color}]{line}"

    def generate_path_lines(self) -> Iterator[str]:
        assert self.change.source is not None
        assert self.change.dest is not None
        source = (
            self.change.source
            if self.change.type == ChangeType.created
            else self.change.dest
        )
        full_path = source / self.change.path
        try:
            yield from full_path.lines
        except UnicodeDecodeError:
            pass


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
        closest = (
            0
            if self.changes
            else 1 + min(sub.closest_nodes() for sub in self.substructures)
        )
        return closest

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
        cls, root_name: str, sub_print_changes: list[PrintChange]
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
            root_path, Change(Path()), sub_print_changes[0].indent_count
        )
        return sub_structure

    def print(self, show_diff: bool = False) -> None:
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
    print_structure: PrintStructure = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.changes = sorted(self.changes, key=lambda c: c.sort_index)
        self.print_structure = PrintStructure.from_changes(self.changes)

    def __iter__(self) -> Iterator[Change]:
        yield from self.changes

    def __bool__(self) -> bool:
        return bool(self.changes)

    @property
    def paths(self) -> list[Path]:
        return [change.path for change in self.changes]

    @classmethod
    def from_patterns(cls, patterns: list[str]) -> Changes:
        return Changes([Change.from_pattern(pattern) for pattern in patterns])

    def print_paths(self, paths: list[Path], indent: int = 0) -> None:
        parts_mapper: dict[str, list[Path]] = {}
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

    def ask_confirm(self, message: str, show_diff: bool = False) -> bool:
        self.print(title="Backup", show_diff=show_diff)
        message = "\n" + message
        return cli.confirm(message, default=True)

    def print(self, title: str | None = None, show_diff: bool = False) -> None:
        if title is not None:
            cli.console.clear()
            cli.console.rule(title)
        self.print_structure.print(show_diff=show_diff)
