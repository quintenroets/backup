import cli

from .path import Path


def export_changes():
    export_resume()


def export_resume():
    for path in Path.resume.rglob("*.docx"):
        if path.export.mtime < path.mtime:
            with cli.status(f"Exporting {path}"):
                export_path(path)
    resume_name = "Resume Quinten Roets.pdf"
    selected_resume = Path.resume / "Main" / resume_name
    main_resume = Path.resume.parent / resume_name
    selected_resume.copy_to(main_resume, only_if_newer=True, include_properties=False)
    if main_resume.mtime > selected_resume.mtime:
        main_resume.mtime = selected_resume.mtime


def export_path(path: Path):
    remote_path = Path.remote / path.export.relative_to(Path.HOME)
    cli.run("rclone --drive-export-formats pdf copy", remote_path, path.parent)
    path.export.mtime = path.mtime
    path.export.tag = "exported"
