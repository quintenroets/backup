from collections.abc import Iterator
from dataclasses import dataclass, field

import cli

from .change import Change
from .path import Path
from .print_structure import PrintStructure


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

    def ask_confirm(self, message: str, *, show_diff: bool = False) -> bool:
        self.print(title="Backup", show_diff=show_diff)
        message = "\n" + message
        return cli.confirm(message, default=True)

    def print(self, title: str | None = None, *, show_diff: bool = False) -> None:
        if title is not None:
            cli.console.clear()
            cli.console.rule(title)
        self.print_structure.print(show_diff=show_diff)
