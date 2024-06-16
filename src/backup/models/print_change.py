from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

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
        return PrintChange(self.path_from_root, self.change, self.indent_count + 1)

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
        except UnicodeDecodeError:  # pragma: nocover
            pass
