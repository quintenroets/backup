from typing import cast

import cli

from backup.backups.remote import Backup
from backup.context import context
from backup.models import Path


def export_changes() -> bool:
    return export_resume()


def export_resume() -> bool:
    for path in Path.resume.rglob("*.docx"):
        if path.with_export_suffix.mtime < path.mtime:
            message_path = path.relative_to(Path.resume)
            with cli.status(f"Exporting {message_path}"):
                export_path(path)

    path = Path.main_resume_pdf
    main_resume_updated = Path.selected_resume_pdf.mtime > path.mtime
    if main_resume_updated:
        Path.selected_resume_pdf.copy_to(path, include_properties=False)
        path.mtime = Path.selected_resume_pdf.mtime
    return cast(bool, main_resume_updated)


def export_path(path: Path) -> None:
    relative_path = path.with_export_suffix.relative_to(context.config.backup_source)
    backup = Backup(path=relative_path, dest=Path.remote)
    backup.export_pdfs()
    path.with_export_suffix.mtime = path.mtime
    path.with_export_suffix.tag = "exported"
