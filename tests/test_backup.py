from hypothesis import HealthCheck, given, settings, strategies

from backup.backup import Backup
from backup.utils import Path
from backup.utils.changes import Change, ChangeType

single_test_settings = settings(
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
    max_examples=1,
    deadline=7000,
)


def fill(folder: Path, content: bytes, number: int = 0):
    path = folder / str(number)
    path.byte_content = content


def fill_folders(folder: Path, folder2: Path, content: bytes, content2: bytes):
    fill(folder, content)
    fill(folder, content, number=1)
    fill(folder, content + content2, number=3)

    fill(folder2, content)
    fill(folder2, content, number=2)
    fill(folder2, content, number=3)


@single_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_status(folder: Path, folder2: Path, content: bytes, content2: bytes):
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2, quiet=True)
    status = backup.status()

    assert Change(Path("1"), ChangeType.created) in status
    assert Change(Path("2"), ChangeType.deleted) in status
    assert Change(Path("3"), ChangeType.modified) in status


@single_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_push(folder: Path, folder2: Path, content: bytes, content2: bytes):
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2, quiet=True)
    backup.push()
    assert not backup.status().paths


@single_test_settings
@given(content=strategies.binary(), content2=strategies.binary(min_size=1))
def test_pull(folder: Path, folder2: Path, content: bytes, content2: bytes):
    fill_folders(folder, folder2, content, content2)
    backup = Backup(folder, folder2, quiet=True)
    backup.pull()
    assert not backup.status().paths
