from dataclasses import dataclass

from backup import backup


@dataclass
class Backup(backup.Backup):
    def export_pdfs(self) -> str:
        arguments = "copy", "--drive-export-formats", "pdf"
        with self.prepared_runner_with_locations(*arguments, reverse=True) as runner:
            return runner.capture_output()
