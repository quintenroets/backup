from .path import Path


def parse_paths(structure):
    tuples = parse_paths_comb(structure, {}, root=Path(""))
    return [t[0] for t in tuples]


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
            subroot = root / name
            drive = Path.docs / "Drive"  # special treatment needed for zip efficiency

            if Path.HOME / subroot == drive:
                subitems = [f.name for f in drive.iterdir()]

            if parts:  # properly set path after / to sublevel
                subitems = [{"/".join(parts): subitems}]
            if subitems:
                self.structures[name] = Structure(subitems, subroot)
            else:
                self.items.append(subroot)
