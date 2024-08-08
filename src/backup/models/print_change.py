from __future__ import annotations

import contextlib
import typing
from dataclasses import dataclass
from functools import cached_property
from typing import cast

import cli

from .change import Change, ChangeType
from .path import Path

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover


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
        return PrintChange(self.path_from_root, self.change, self.indent_count + 1)

    @property
    def symbol(self) -> str:
        return self.change.type.symbol if self.change.path.parts else "\u2022"

    @cached_property
    def path_message(self) -> str:
        root = Path("/")
        relative_home = Path.HOME.relative_to(root)
        path = (
            Path("HOME") / self.path.relative_to(relative_home)
            if self.path.is_relative_to(relative_home)
            else self.path
        )
        return str(path)

    @cached_property
    def whitespace(self) -> str:
        return self.indent * self.indent_count

    def print(self, *, show_diff: bool = False) -> None:
        not_usable_width = self.whitespace + self.symbol + " " + "-"
        available_width = cli.console.width - len(not_usable_width)
        message_chunks = [
            self.path_message[start : start + available_width]
            for start in range(0, len(self.path_message), available_width)
        ]
        lines = self.format_lines(message_chunks)
        message = "\n".join(lines)
        cli.console.print(message)
        if show_diff and self.change.path.parts:
            self.print_diff()

    def format_lines(self, lines: list[str]) -> Iterator[str]:
        color = self.change.type.color if self.change.path.parts else "black"
        last_chunk_index = len(lines) - 1
        for i, message in enumerate(lines):
            prefix = f"{self.symbol} " if i == 0 else "  "
            need_suffix = i < last_chunk_index and " " not in (
                message[-1],
                lines[i + 1][0],
            )
            suffix = "-" if need_suffix else ""
            yield f"{self.whitespace}{prefix}[bold {color}]{message}{suffix}"

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
                diff_line = line[1:].strip()
                if change_type != ChangeType.preserved:
                    diff_line = f"{change_type.symbol} {diff_line}"
                yield f"[{change_type.color}]{diff_line}"

    def generate_path_lines(self) -> Iterator[str]:
        source = cast(Path, self.change.source)
        dest = cast(Path, self.change.dest)
        source = source if self.change.type == ChangeType.created else dest
        full_path = source / self.change.path
        with contextlib.suppress(UnicodeDecodeError):
            yield from full_path.lines
