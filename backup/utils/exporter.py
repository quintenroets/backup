import cli

from backup.backups.remote import Backup

from .path import Path


def export_changes():
    return export_resume()


def export_resume():
    for path in Path.resume.rglob("*.docx"):
        if path.export.mtime < path.mtime:
            message_path = path.relative_to(Path.resume)
            with cli.status(f"Exporting {message_path}"):
                export_path(path)

    selected_resume = Path.resume / "Main" / Path.main_resume_pdf.name
    main_resume_updated = selected_resume.mtime > Path.main_resume_pdf.mtime
    if main_resume_updated:
        selected_resume.copy_to(Path.main_resume_pdf, include_properties=False)
        Path.main_resume_pdf.mtime = selected_resume.mtime
    return main_resume_updated


def export_path(path: Path):
    relative_path = path.export.relative_to(Backup.source)
    backup = Backup(path=relative_path, reverse=True, quiet=True)
    backup.export_pdfs()
    path.export.mtime = path.mtime
    path.export.tag = "exported"
