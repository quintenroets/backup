from content import byte_content
from utils import HealthCheck, settings

from backup.backup import Backup
from backup.utils import Path

ignore_fixture_warning = settings(
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
    max_examples=1,
    deadline=3000,
)


@ignore_fixture_warning
@byte_content
def test_backup(folder: Path, folder2: Path, content: bytes):
    filename = folder.name
    subpath = folder / filename
    subpath2 = folder2 / filename
    for test_subpath in (subpath, subpath2):
        test_subpath.byte_content = content

    diff = Backup(folder, folder2).check()
    print(diff)
