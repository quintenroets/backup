from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest
from backup import main
from backup.context.context import Context


@patch("backup.backups.backup.Backup.run_action")
def test_main(_: MagicMock) -> None:
    main()


@pytest.fixture
def open_urls_context(test_context: Context) -> Iterator[Context]:
    test_context.options.configure = True
    yield test_context
    test_context.options.configure = False


@patch("cli.open_urls")
def test_url_open(_: MagicMock, open_urls_context: Context) -> None:
    main()
