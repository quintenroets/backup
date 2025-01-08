import os
from dataclasses import dataclass, field


@dataclass
class Secrets:
    rclone: str
