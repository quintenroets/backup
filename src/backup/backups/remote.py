from dataclasses import dataclass

import cli

from .. import backup


@dataclass
class Backup(backup.Backup):
    def export_pdfs(self) -> str:
        command = self.create_cli_command(
            "copy", "--drive-export-formats", "pdf", reverse=True
        )
        return cli.capture_output(command)
