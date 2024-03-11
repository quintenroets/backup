from dataclasses import dataclass, field
from typing import ClassVar

from ....utils import Path
from .path import (
    CommentsRemovedChecker,
    KwalletChecker,
    PathChecker,
    RcloneChecker,
    UserPlaceChecker,
)


def calculate_checkers():
    checkers_iterator = generate_checkers()
    return {path: checker for path, checker in checkers_iterator}


def generate_checkers():
    nested_checkers = {
        ".config": {
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
        },
        ".local/share": {
            "user-places.xbel": UserPlaceChecker(),
            "kwalletd/kdewallet.kwl": KwalletChecker(),
        },
    }

    for folder, folder_checkers in nested_checkers.items():
        for sub_path, checker in folder_checkers.items():
            path = Path(folder) / sub_path
            yield path, checker


@dataclass
class Checker:
    checkers: ClassVar[dict[Path, PathChecker]] = field(default=calculate_checkers())
