import fnmatch

import pytest

from backup.backup.models import Ignores

patterns = ["*.pyc", "*/node_modules/*", "scratch/*", "*.[oa]", "cache?"]

relative_paths = [
    "user/module.pyc",
    "user/project/node_modules/left-pad/index.js",
    "scratch/session",
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


def test_anchored_pattern_matches_from_the_source_root() -> None:
    """An absolute path would never match: fnmatch anchors at the start."""
    ignores = Ignores(patterns=["scratch/*"])
    assert ignores.matches("scratch/session", name="session")
    assert not ignores.matches("/home/user/scratch/session", name="session")


def test_without_patterns_nothing_matches() -> None:
    assert not Ignores().matches("any/path", name="any")


def test_names_match_on_basename_only() -> None:
    ignores = Ignores(names=["__pycache__"])
    assert ignores.matches("user/__pycache__", name="__pycache__")
    assert not ignores.matches("user/__pycache__/module.pyc", name="module.pyc")
