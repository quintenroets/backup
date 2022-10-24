import json
from types import FunctionType
from typing import Dict, Set

import cli

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


def kwallet_content():
    def get_folder_info(folder):
        items = cli.lines("kwallet-query -l kdewallet -f", folder)
        return {
            item: cli.get("kwallet-query kdewallet -r", item, "-f", folder)
            for item in items
        }

    folders = ("Network Management", "Passwords", "ksshaskpass")
    info = {folder: get_folder_info(folder) for folder in folders}
    info = json.dumps(info)
    return info


def rclone_content():
    config_lines = cli.lines("rclone config show")
    nonvolatile_config_lines = [l for l in config_lines if "refresh_token" not in l]
    return nonvolatile_config_lines


def check_wallet(path: Path):
    return check_hash(path, kwallet_content)


def check_rclone(path: Path):
    return check_hash(path, rclone_content)


def calculate_hash(path: Path, content_generator):
    import hashlib  # noqa: autoimport
    import json  # noqa: autoimport

    content = content_generator()
    content_bytes = json.dumps(content).encode()
    hash_value = hashlib.new("sha512", data=content_bytes).hexdigest()
    return hash_value


def check_hash(path: Path, content_generator):
    hash_path = path.hash_path
    # compare generated hash with saved hash
    if path.is_relative_to(Path.backup_cache):
        hash_value = hash_path.text
    else:
        hash_value = calculate_hash(path, content_generator)
        if hash_path.text != hash_value:
            hash_path.text = hash_value
    return hash_value


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
        ".local/share/kwalletd/kdewallet.kwl": check_wallet,
        ".config/rclone/rclone.conf": check_rclone,
    }
    return {Path(k): v for k, v in checkers.items()}


def reduce(items: Set[Path]):
    checkers = custom_checkers()
    to_remove = set({})
    new_items = set({})

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
                mirror.touch(mtime=full_path.mtime)
                to_remove.add(item)
            elif full_path.hash_path.exists():
                new_items.add(full_path.hash_path.relative_to(Path.HOME))

    return (items | new_items) - to_remove
