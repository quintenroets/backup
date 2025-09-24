import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated

import cli
import typer

from backup.context import context
from backup.utils.setup import check_setup


class Help:
    remote = "name of remote to mount"
    path = "local path to mount remote to"
    rclone_secret = "decryption key for rclone configuration"  # noqa: S105
    cache_mode = "vfs-cache-mode option for rclone"


@dataclass
class Mounter:
    remote: Annotated[str, typer.Option(help=Help.remote)] = "backupmaster"
    path: Annotated[Path, typer.Option(help=Help.path)] = field(default_factory=Path)
    rclone_secret: Annotated[str, typer.Option(help=Help.rclone_secret)] = field(
        default_factory=lambda: context.secrets.rclone,
    )
    cache_mode: str = "writes"

    def run(self) -> None:
        """
        Mount remote to local path.
        """
        check_setup()
        self.check_path()
        env = os.environ | {"RCLONE_CONFIG_PASS": self.rclone_secret}
        env.pop("RCLONE_PASSWORD_COMMAND", None)
        remote = f"{self.remote}:" if ":" not in self.remote else self.remote
        options = {"vfs-cache-mode": self.cache_mode}
        cli.launch("rclone mount", remote, self.path, options, env=env)
        time.sleep(0.5)

    def check_path(self) -> None:
        if not self.path.parts:
            self.path = Path("/") / "media" / self.remote.split(":")[0].lower()
        if not self.path.exists():
            self.create_path()

    def create_path(self) -> None:
        created_root = self.path
        while not created_root.parent.exists():
            created_root = created_root.parent
        username = "runner" if "GITHUB_ACTIONS" in os.environ else os.getlogin()
        commands = (
            f"mkdir -p {self.path}",
            f"chown {username}:{username} -R {created_root}",
            f"chmod 777 -R {created_root}",
        )
        for command in commands:
            cli.run(command, root=True)
