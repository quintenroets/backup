import fnmatch

import pytest

from backup.models import Ignores

patterns = ["*.pyc", "*/node_modules/*", "scratch/*", "*.[oa]", "cache?"]

relative_paths = [
    "user/module.pyc",
    "user/project/node_modules/left-pad/index.js",
    "scratch/session",
    "/home/user/scratch/session",
    "user/build/main.o",
    "cache1",
    "user/module.py",
    "user/node_modules",
    "cache12",
]


@pytest.mark.parametrize("relative", relative_paths)
def test_patterns_match_fnmatch(relative: str) -> None:
    expected = any(fnmatch.fnmatch(relative, pattern) for pattern in patterns)
    assert Ignores(patterns=patterns).matches(relative, name="irrelevant") == expected
