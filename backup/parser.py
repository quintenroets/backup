from .path import Path

def parse_paths(structure):
    struct_list = [{Path(""): structure}]
    finished = False

    while not finished:
        new_struct_list = []
        finished = True

        for struct in struct_list:
            if not isinstance(struct, dict): # normal complete path
                new_struct_list.append(struct)
            else:
                for root, items in struct.items():
                    for item in items:
                        if not isinstance(item, dict):
                            new_item = root / item
                        else:
                            finished = False
                            new_item = {
                                root / subroot: subitems for subroot, subitems in item.items()
                            }
                        new_struct_list.append(new_item)

        struct_list = new_struct_list

    paths = struct_list
    return paths


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