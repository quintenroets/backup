from collections.abc import Iterator
from unittest.mock import MagicMock, patch

import pytest

from backup.context.context import Context
from backup.main.main import main
from backup.context.action import Action


def test_main(test_context: Context) -> None:
    methods = {"push": Action.push, "pull": Action.pull, "status": Action.status}
    for method_name, action in methods.items():
        with patch(f"backup.backup.backup.Backup.{method_name}") as mocked_run:
            test_context.options.action = action
            main()
            mocked_run.assert_called_once()
    test_context.options.action = Action.push


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
