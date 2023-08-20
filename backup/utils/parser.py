import os

from .path import Path


def parse_paths(structure):
    tuples = parse_paths_comb(structure, {})
    return [t[0] for t in tuples]


def parse_paths_comb(include, exclude, root=None):
    paths = []
    todo = [(Structure(include, root=root), Structure(exclude, root=root))]

    while todo:
        include, exclude = todo.pop(0)
        paths += [(it, True) for it in include.items] + [
            (it, False) for it in exclude.items
        ]
        todo += [
            tuple(s.structures.get(sub_root, Structure([])) for s in (include, exclude))
            for sub_root in (include.structures | exclude.structures)
        ]
    return paths[::-1]


class Structure:
    def __init__(self, items, root=None):
        if root is None:
            root = Path("")

        self.items = []
        self.structures = {}

        for item in items:
            if not isinstance(item, dict):
                item = {item: []}

            name, sub_items = next(iter(item.items()))

            name, *parts = name.split("/")
            name = replace_special_characters(root, name)
            sub_root = root / name
            if parts:
                # item was multiple directories deep
                # => add first part and go one level deeper
                sub_items = [{os.sep.join(parts): sub_items}]
            if sub_items:
                self.structures[name] = Structure(sub_items, sub_root)
            else:
                self.items.append(sub_root)


def replace_special_characters(root: Path, name: str):
    VERSION_KEYWORD = "__VERSION__"
    if VERSION_KEYWORD in name:
        name_start = name.split(VERSION_KEYWORD)[0]
        absolute_root = Path.HOME / root
        true_paths = absolute_root.glob(f"{name_start}*")
        true_paths: list[Path] = sorted(list(true_paths), key=lambda path: -path.mtime)
        name = true_paths[0].name

    return name
