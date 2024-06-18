import os
import time
from dataclasses import dataclass, field
from typing import Annotated

import cli
import typer

from backup.models import Path
from backup.utils.setup import check_setup

from ..context import context


class Help:
    remote = "name of remote to mount"
    path = "local path to mount remote to"
    rclone_secret = "decryption key for rclone configuration"


@dataclass
class Mounter:
    remote: Annotated[str, typer.Option(help=Help.remote)] = "backup"
    path: Annotated[Path, typer.Option(help=Help.path)] = field(default_factory=Path)
    rclone_secret: Annotated[str, typer.Option(help=Help.rclone_secret)] = field(
        default_factory=lambda: context.secrets.rclone
    )

    def run(self) -> None:
        """
        Mount remote to local path.
        """
        check_setup()
        self.check_path()
        env = os.environ | {"RCLONE_CONFIG_PASS": self.rclone_secret}
        env.pop("RCLONE_PASSWORD_COMMAND", None)
        remote = f"{self.remote}:" if ":" not in self.remote else self.remote
        cli.launch("rclone mount", remote, self.path, env=env)
        time.sleep(0.5)

    def check_path(self) -> None:
        if not self.path.parts:
            self.path = Path("/") / "media" / self.remote.split(":")[0].lower()
        if not self.path.exists():
            username = "runner" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
            commands = f"-u {username} mkdir -p", "chmod 777"
            for command in commands:
                cli.run(command, self.path, root=True)
