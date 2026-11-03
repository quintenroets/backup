from dataclasses import dataclass
from enum import Enum, StrEnum


class Action(StrEnum):
    push = "push"
    pull = "pull"


class ChangeType(Enum):
    created = 0, "green", "+"
    modified = 1, "blue", "*"
    deleted = 2, "red", "-"

    def __init__(self, sort_order: int, color: str, symbol: str) -> None:
        self.sort_order = sort_order
        self.color = color
        self.symbol = symbol


@dataclass
class Change:
    path: str
    type: ChangeType
    conflict: bool = False
