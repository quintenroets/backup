import cli

from .path import Path


def export_changes():
    export_resume()


def export_resume():
    for path in Path.resume.rglob("*.docx"):
        if path.export.mtime < path.mtime:
            export_path(path)
    resume_name = "Resume Quinten Roets.pdf"
    main_resume = Path.resume / "Research" / resume_name
    main_resume.copy_to(Path.resume.parent / resume_name, only_if_newer=True)


def export_path(path: Path):
    remote_path = Path.remote / path.export.relative_to(Path.HOME)
    cli.run("rclone --drive-export-formats pdf copy", remote_path, path.parent)
    path.export.mtime = path.mtime
