import json

from backup.backup import Backup
from backup.models import Change, ChangeType, Path
from hypothesis import HealthCheck, given, settings, strategies

slow_test_settings = settings(
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
    max_examples=3,
    deadline=7000,
)


def fill(folder: Path, content: bytes, number: int = 0) -> None:
    path = folder / str(number)
    path.byte_content = content


def fill_folders(folder: Path, folder2: Path, content: bytes, content2: bytes) -> None:
    fill(folder, content)
    fill(folder, content, number=1)
    fill(folder, content + content2, number=3)

    fill(folder2, content)
    fill(folder2, content, number=2)
    fill(folder2, content, number=3)


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_status(folder: Path, folder2: Path, content: bytes, content2: bytes) -> None:
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2)
    status = backup.capture_status(quiet=True)

    expected_changes = (
        Change(Path("1"), ChangeType.created),
        Change(Path("2"), ChangeType.deleted),
        Change(Path("3"), ChangeType.modified),
    )
    for change in status:
        change.source = change.dest = None
    for change in expected_changes:
        assert change in status


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_push(folder: Path, folder2: Path, content: bytes, content2: bytes) -> None:
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2)
    backup.capture_push()
    assert not backup.capture_status().paths


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_pull(folder: Path, folder2: Path, content: bytes, content2: bytes) -> None:
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2)
    backup.capture_pull()
    assert not backup.capture_status().paths


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_ls(folder: Path, folder2: Path, content: bytes, content2: bytes) -> None:
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2)
    path = folder / "0"
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_single_file_copy(
    folder: Path, folder2: Path, content: bytes, content2: bytes
) -> None:
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2)
    backup.capture_output("copyto", folder / "0", folder2 / "0")
