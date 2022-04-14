from typing import List

from .path import Path


def parse_paths(structure):
    tuples = parse_paths_comb(structure, {}, root=Path(""))
    return [t[0] for t in tuples]


def is_drive_path(subpath: Path):
    return Path.HOME / subpath == Path.drive


def replace_subitems(subroot: Path, subitems: List[str]) -> List[str]:
    if is_drive_path(subroot):
        # special treatment needed for zip efficiency
        subitems = [f.name for f in Path.drive.iterdir()]
    return subitems


def replace_special_characters(root: Path, name: str):
    VERSION_KEYWORD = "__VERSION__"
    if VERSION_KEYWORD in name:
        name_start = name.split(VERSION_KEYWORD)[0]
        absolute_root = Path.HOME / root
        true_paths = absolute_root.glob(f"{name_start}*")
        true_paths: List[Path] = sorted(list(true_paths), key=lambda path: -path.mtime)
        name = true_paths[0].name

    return name


def make_filters(
    includes=None, excludes=None, recursive=True, include_others=False, root=Path.HOME
):
    mapping = {"+": includes or [], "-": excludes or []}
    filters = []
    for symbol, paths in mapping.items():
        for path in paths:
            addition = "/**" if recursive and (root / path).is_dir() else ""
            filter = f"{symbol} /{path}{addition}"
            filters.append(filter)

    if include_others:
        filters.append("+ **")

    return filters


def parse_paths_comb(include, exclude, root=None):
    paths = []
    todo = [(Structure(include, root=root), Structure(exclude, root=root))]

    while todo:
        include, exclude = todo.pop(0)
        paths += [(it, True) for it in include.items] + [
            (it, False) for it in exclude.items
        ]
        todo += [
            tuple(s.structures.get(subroot, Structure([])) for s in (include, exclude))
            for subroot in (include.structures | exclude.structures)
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

            name, subitems = next(iter(item.items()))

            name, *parts = name.split("/")
            name = replace_special_characters(root, name)
            subroot = root / name
            subitems = replace_subitems(subroot, subitems)
            if parts:
                # item was multiple directories deep => add first part and go one level deeper
                subitems = [{"/".join(parts): subitems}]
            if subitems:
                self.structures[name] = Structure(subitems, subroot)
            else:
                self.items.append(subroot)
