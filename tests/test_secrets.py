from collections.abc import Iterator
from unittest.mock import patch

import pytest

from backup.context import context


@pytest.fixture
def _cleared_rclone_env() -> Iterator[None]:
    context.__dict__.pop("rclone_env", None)
    yield
    context.__dict__.pop("rclone_env", None)


@pytest.mark.usefixtures("_cleared_rclone_env")
def test_load_rclone_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RCLONE_PASSWORD_COMMAND", "command")
    with patch("backup.context.SecretLoader") as mocked_loader:
        mocked_loader.return_value.load.return_value = "secret"
        env = context.rclone_env
    assert env["RCLONE_CONFIG_PASS"] == "secret"  # noqa: S105
    assert "RCLONE_PASSWORD_COMMAND" not in env
