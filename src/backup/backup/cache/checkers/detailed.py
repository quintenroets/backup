from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import ClassVar

from backup.models import Path

from .path import (
    CommentsRemovedChecker,
    KwalletChecker,
    PathChecker,
    RcloneChecker,
    UserPlaceChecker,
)


def calculate_checkers() -> dict[Path, PathChecker]:
    checkers_iterator = generate_checkers()
    return dict(checkers_iterator)


def generate_checkers() -> Iterator[tuple[Path, PathChecker]]:
    config_checkers = {
        "gtkrc": CommentsRemovedChecker(),
        "gtkrc-2.0": CommentsRemovedChecker(),
        "katerc": PathChecker(
            ignore_sections=("KTextEditor::Search", "KFileDialog Settings"),
            ignore_lines=("Color Theme=",),
        ),
        "katevirc": PathChecker(
            ignore_lines=("ViRegisterContents=",),
        ),
        "kdeglobals": PathChecker(
            ignore_sections=("DirSelect Dialog",),
        ),
        "ksmserverrc": PathChecker(
            ignore_sections=("Session: saved at previous logout",),
        ),
        "kglobalshortcutsrc": PathChecker(
            ignore_sections=("ActivityManager", "mediacontrol"),
            ignore_lines=("activate widget",),
        ),
        "plasmashellrc": PathChecker(
            ignore_sections=("PlasmaTransientsConfig",),
        ),
        "rclone/rclone.conf": RcloneChecker(),
    }
    local_checkers = {
        "user-places.xbel": UserPlaceChecker(),
        "kwalletd/kdewallet.kwl": KwalletChecker(),
    }
    nested_checkers = {".config": config_checkers, ".local/share": local_checkers}

    for folder_str, folder_checkers in nested_checkers.items():
        folder = Path(folder_str)
        for sub_path, checker in folder_checkers.items():
            yield folder / sub_path, checker


@dataclass
class Checker:
    checkers: ClassVar[dict[Path, PathChecker]] = field(default=calculate_checkers())
