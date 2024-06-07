import json

from backup.backup import Backup
from backup.models import Change, ChangeType, Path
from hypothesis import HealthCheck, Phase, given, settings, strategies

slow_test_settings = settings(
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
    max_examples=3,
    deadline=7000,
    phases=(Phase.explicit, Phase.generate),
)


def fill(directory: Path, content: bytes, number: int = 0) -> None:
    path = directory / str(number)
    path.byte_content = content


def fill_directories(
    directory: Path, directory2: Path, content: bytes, content2: bytes
) -> None:
    fill(directory, content)
    fill(directory, content, number=1)
    fill(directory, content + content2, number=3)

    fill(directory2, content)
    fill(directory2, content, number=2)
    fill(directory2, content, number=3)


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_status(
    directory: Path, directory2: Path, content: bytes, content2: bytes
) -> None:
    fill_directories(directory, directory2, content, content2)
    backup = Backup(directory, directory2)
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
def test_push(
    directory: Path, directory2: Path, content: bytes, content2: bytes
) -> None:
    fill_directories(directory, directory2, content, content2)
    backup = Backup(directory, directory2)
    backup.capture_push()
    backup.push()
    assert not backup.capture_status().paths


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_pull(
    directory: Path, directory2: Path, content: bytes, content2: bytes
) -> None:
    fill_directories(directory, directory2, content, content2)
    backup = Backup(directory, directory2)
    backup.capture_pull()
    backup.pull()
    assert not backup.capture_status().paths


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_ls(directory: Path, directory2: Path, content: bytes, content2: bytes) -> None:
    fill_directories(directory, directory2, content, content2)
    backup = Backup(directory, directory2)
    path = directory / "0"
    file_info = backup.capture_output("lsjson", path)
    parsed_file_info = json.loads(file_info)
    assert parsed_file_info[0]["Name"] == path.name


@slow_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_single_file_copy(
    directory: Path, directory2: Path, content: bytes, content2: bytes
) -> None:
    fill_directories(directory, directory2, content, content2)
    backup = Backup(directory, directory2)
    backup.capture_output("copyto", directory / "0", directory2 / "0")
