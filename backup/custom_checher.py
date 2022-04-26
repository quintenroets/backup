from types import FunctionType
from typing import Dict, Set

from .path import Path


def check_kate(path: Path):
    ignore_sections = ("[KTextEditor::Search]", "[KFileDialog Settings]")
    lines = path.lines
    header_indices = [i for i, line in enumerate(lines) if line.startswith("[")]

    non_volatile_sections = []
    for start, end in zip(header_indices, header_indices[1:]):
        section = lines[start:end]
        if section[0] not in ignore_sections:
            non_volatile_sections.append(section)

    return non_volatile_sections


def custom_checkers() -> Dict[Path, FunctionType]:
    checkers = {".config/katerc": check_kate}
    return {Path(k): v for k, v in checkers.items()}


def reduce(items: Set[Path]):
    reduced_items = []
    checkers = custom_checkers()
    for item in items:
        if item not in checkers:
            reduced_items.append(item)
        else:
            checker = checkers[item]
            full_path = Path.HOME / item
            mirror = Path.backup_cache / item
            if checker(full_path) != checker(mirror):
                reduced_items.append(item)

    return items
