from backup.utils import Path, exporter


def test_status():
    exporter.export_changes()
    for path in Path.resume.rglob("*.docx"):
        assert path.with_suffix(".pdf").mtime == path.mtime
