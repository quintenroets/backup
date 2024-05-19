from dataclasses import dataclass

import cli

from .. import backup


@dataclass
class Backup(backup.Backup):
    def export_pdfs(self) -> str:
        with self.prepared_command_with_locations(
            "copy", "--drive-export-formats", "pdf", reverse=True
        ) as command:
            return cli.capture_output(*command)
