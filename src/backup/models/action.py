from enum import Enum


class Action(Enum):
    status = "status"
    push = "push"
    pull = "pull"
    diff = "diff"
