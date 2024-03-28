from dataclasses import dataclass

from .. import backup


@dataclass
class Backup(backup.Backup):
    def export_pdfs(self):
        return self.start("copy", "--drive-export-formats", "pdf")
