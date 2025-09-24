from typing import cast
from unittest.mock import MagicMock, patch

from backup.models import Path
from backup.syncer import Syncer
from backup.utils import exporter


def create_empty_pdf(syncer: Syncer) -> None:
    path = syncer.config.source / cast("Path", syncer.config.path)
    path.touch()


def add_mocked_document() -> None:
    Path.selected_resume_pdf.with_suffix(".docx").touch()


@patch("xattr.xattr.set")
@patch.object(Syncer, "export_pdfs", autospec=True)
def test_export(mocked_export: MagicMock, mocked_xattr: MagicMock) -> None:
    mocked_export.side_effect = create_empty_pdf
    add_mocked_document()
    exporter.export_resume()
    for path in Path.resume.rglob("*.docx"):
        assert path.with_suffix(".pdf").mtime == path.mtime
    mocked_xattr.assert_called()


@patch("cli.run")
def test_export_pdfs(mocked_run: MagicMock, mocked_syncer: Syncer) -> None:
    mocked_syncer.export_pdfs()
    mocked_run.assert_not_called()
