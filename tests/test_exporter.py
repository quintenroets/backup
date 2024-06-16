from typing import cast
from unittest.mock import MagicMock, patch

from backup.backups import remote
from backup.context.context import Context
from backup.models import Path
from backup.utils import exporter


def create_empty_pdf(self: remote.Backup) -> None:
    path = self.source / cast(Path, self.path)
    path.touch()


@patch("xattr.xattr.set")
@patch.object(remote.Backup, "export_pdfs", autospec=True)
def test_export(mocked_export: MagicMock, _: MagicMock, test_context: Context) -> None:
    mocked_export.side_effect = create_empty_pdf
    add_mocked_document(test_context)
    exporter.export_changes()
    for path in Path.resume.rglob("*.docx"):
        assert path.with_suffix(".pdf").mtime == path.mtime


def add_mocked_document(test_context: Context) -> None:
    Path.selected_resume_pdf.with_suffix(".docx").touch()


@patch("cli.run")
def test_export_pdfs(_: MagicMock, test_context: Context) -> None:
    remote.Backup().export_pdfs()
