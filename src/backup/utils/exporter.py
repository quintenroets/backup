from typing import cast

import cli

from backup.backups.remote import Backup

from ..context import context
from ..models import Path


def export_changes() -> bool:
    return export_resume()


def export_resume() -> bool:
    for path in Path.resume.rglob("*.docx"):
        if path.with_export_suffix.mtime < path.mtime:
            message_path = path.relative_to(Path.resume)
            with cli.status(f"Exporting {message_path}"):
                export_path(path)

    selected_resume = Path.resume / "Main" / Path.main_resume_pdf.name
    main_resume_updated = selected_resume.mtime > Path.main_resume_pdf.mtime
    if main_resume_updated:
        selected_resume.copy_to(Path.main_resume_pdf, include_properties=False)
        Path.main_resume_pdf.mtime = selected_resume.mtime
    return cast(bool, main_resume_updated)


def export_path(path: Path) -> None:
    relative_path = path.with_export_suffix.relative_to(context.config.backup_source)
    backup = Backup(path=relative_path)
    backup.export_pdfs()
    path.with_export_suffix.mtime = path.mtime
    path.with_export_suffix.tag = "exported"
