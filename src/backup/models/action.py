from enum import Enum


class Action(str, Enum):
    status = "status"
    push = "push"
    pull = "pull"
    diff = "diff"
