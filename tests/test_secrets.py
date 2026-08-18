from collections.abc import Iterator
from unittest.mock import patch

import pytest

from backup.syncer import load_rclone_env


@pytest.fixture
def _cleared_rclone_env() -> Iterator[None]:
    load_rclone_env.cache_clear()
    yield
    load_rclone_env.cache_clear()


@pytest.mark.usefixtures("_cleared_rclone_env")
def test_load_rclone_password(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("RCLONE_PASSWORD_COMMAND", "command")
    with patch("backup.syncer.cli_runner.SecretLoader") as mocked_loader:
        mocked_loader.return_value.load.return_value = "secret"
        env = load_rclone_env()
    assert env["RCLONE_CONFIG_PASS"] == "secret"  # noqa: S105
    assert "RCLONE_PASSWORD_COMMAND" not in env
