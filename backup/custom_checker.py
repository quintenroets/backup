from types import FunctionType
from typing import Dict, Set

from .path import Path


def check_ksmserverrc(path: Path):
    return filter_sections(
        path, ignore_sections=("[Session: saved at previous logout]",)
    )


def check_kate(path: Path):
    sections = filter_sections(
        path,
        ignore_sections=("[KTextEditor::Search]", "[KFileDialog Settings]"),
        ignore_lines=("Color Theme=",),
    )

    return sections


def filter_sections(path: Path, ignore_sections=(), ignore_lines=()):
    lines = path.lines
    header_indices = [i for i, line in enumerate(lines) if line.startswith("[")]

    non_volatile_sections = []
    for start, end in zip(header_indices, header_indices[1:]):
        section = lines[start:end]
        if section[0] not in ignore_sections:
            non_volatile_sections.append(section)

    for section in non_volatile_sections:
        for line in section:
            if any(l in line for l in ignore_lines):
                section.remove(line)

    return non_volatile_sections


def remove_comments(path: Path):
    return filter_sections(path, ignore_lines=("+",))


def check_user_places(path: Path):
    from bs4 import BeautifulSoup  # noqa: autoimport

    text = path.text
    soup = BeautifulSoup(text, features="lxml")
    tags = []

    for tag in soup.find_all("bookmark"):
        href = tag.get("href")
        ignore_names = ("tags", "kdeconnect")
        if not any([name in href for name in ignore_names]):
            tags.append(str(tag))
    return tags


def custom_checkers() -> Dict[Path, FunctionType]:
    checkers = {
        ".config/gtkrc": remove_comments,
        ".config/gtkrc-2.0": remove_comments,
        ".config/katerc": check_kate,
        ".config/ksmserverrc": check_ksmserverrc,
        ".config/kglobalshortcutsrc": lambda path: filter_sections(
            path, ignore_sections=("[ActivityManager]", "[mediacontrol]")
        ),
        ".local/share/user-places.xbel": check_user_places,
    }
    return {Path(k): v for k, v in checkers.items()}


def reduce(items: Set[Path]):
    checkers = custom_checkers()
    to_remove = set({})
    for item in items:
        full_item = Path.HOME / item
        if full_item.is_relative_to(Path.profiles):
            profile_item = full_item.relative_to(Path.profiles)
            profile_item = profile_item.relative_to(profile_item.parts[0])
        else:
            profile_item = None

        checker = checkers.get(item) or checkers.get(profile_item)
        if checker:
            full_path: Path = Path.HOME / item
            mirror = Path.backup_cache / item

            if checker(full_path) == checker(mirror):
                full_path.copy_to(mirror)
                to_remove.add(item)

    return items - to_remove
