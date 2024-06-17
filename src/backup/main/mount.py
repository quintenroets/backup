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
    path: Annotated[Path | None, typer.Option(help=Help.path)] = None
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
        cli.launch("rclone mount", env=env)
        time.sleep(5)
        cli.run("ls", self.path)

    def check_path(self) -> None:
        if self.path is None:
            self.path = Path("/") / "media" / self.remote.split(":")[0].capitalize()
        if not self.path.exists():
            username = "root" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
            commands = f"sudo mkdir {self.path}", f"sudo chown {username} {self.path}"
            cli.run_commands(*commands)
