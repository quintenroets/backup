from backup.models import Path
from backup.utils import exporter


def test_export() -> None:
    for path in Path.resume.rglob("*.docx"):
        path.with_suffix(".pdf").unlink(missing_ok=True)
    exporter.export_changes()
    for path in Path.resume.rglob("*.docx"):
        assert path.with_suffix(".pdf").mtime == path.mtime
