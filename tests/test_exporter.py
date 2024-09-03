from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from backup.backups import remote
from backup.models import Path
from backup.utils import exporter


def create_empty_pdf(self: remote.Backup) -> None:
    path = self.source / cast(Path, self.path)
    path.touch()


@patch("xattr.xattr.set")
@patch.object(remote.Backup, "export_pdfs", autospec=True)
@pytest.mark.usefixtures("test_context")
def test_export(mocked_export: MagicMock, mocked_xattr: MagicMock) -> None:
    mocked_export.side_effect = create_empty_pdf
    add_mocked_document()
    exporter.export_changes()
    for path in Path.resume.rglob("*.docx"):
        assert path.with_suffix(".pdf").mtime == path.mtime
    mocked_xattr.assert_called()


def add_mocked_document() -> None:
    Path.selected_resume_pdf.with_suffix(".docx").touch()


@patch("cli.run")
@pytest.mark.usefixtures("test_context")
def test_export_pdfs(mocked_run: MagicMock) -> None:
    remote.Backup().export_pdfs()
    mocked_run.assert_not_called()
