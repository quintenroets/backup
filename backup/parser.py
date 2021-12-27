from .path import Path

def parse_paths(structure):
    return parse_paths_comb(structure, {}, root=Path(""))


def make_filters(includes=[], excludes=[], recursive=True, include_others=False):
    addition = "**" if recursive else ""
    mapping = {"+": includes, "-": excludes}
    filters = []
    for symbol, paths in mapping.items():
        for path in paths:
            filter = f'{symbol} /{path}{addition}'
            filters.append(filter)

    if include_others:
        filters.append("+ **")

    return filters


def parse_paths_comb(include, exclude, root=None):
    paths = []
    todo = [(Structure(include, root=root), Structure(exclude, root=root))]

    while todo:
        include, exclude = todo.pop(0)
        paths += [(it, True) for it in include.items] + [(it, False) for it in exclude.items]
        todo += [
            tuple(s.structures.get(subroot, Structure([])) for s in (include, exclude))
            for subroot in (include.structures | exclude.structures)
        ]

    return paths[::-1]


def calculate_difference(new, old):
    new_copy = {k: v for k, v in new.items()}
    old_copy = {k: v for k, v in old.items()}

    for path in old:
        if path in new and new[path] == old[path]:
            old_copy.pop(path)
            new_copy.pop(path)

    paths = set(list(old_copy) + list(new_copy))
    return paths


class Structure:
    def __init__(self, items, root=None):
        if root is None:
            root = Path("")

        self.items = []
        self.structures = {}

        for item in items:
            if isinstance(item, dict):
                subroot, subitems = next(iter(item.items()))
                subroot, *parts = subroot.split("/")
                if parts: # properly set path after / to sublevel
                    subitems = [{"/".join(parts): subitems}]
                item = Structure(subitems, root / subroot)
                self.structures[subroot] = item
            else:
                self.items.append(root / item)