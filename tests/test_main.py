from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from backup.context.context import Context
from backup.main.main import main


@patch("backup.backups.backup.Backup.run_action")
def test_main(mocked_run: MagicMock) -> None:
    main()
    mocked_run.assert_called_once()


@pytest.fixture
def open_urls_context(test_context: Context) -> Iterator[Context]:
    test_context.options.configure = True
    yield test_context
    test_context.options.configure = False


@patch("cli.open_urls")
@pytest.mark.usefixtures("open_urls_context")
def test_url_open(mocked_open: MagicMock) -> None:
    main()
    mocked_open.assert_called_once()
