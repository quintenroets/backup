import os
from dataclasses import dataclass, field


@dataclass
<<<<<<< HEAD
=======
class ApiSecrets:
    token: str = field(default_factory=lambda: os.environ.get("API_TOKEN", ""))


@dataclass
>>>>>>> template
class Secrets:
    rclone: str
