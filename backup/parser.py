from libs.path import Path

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

def make_filters(paths, include=True, recursive=True):
    symbol = "+" if include else "-"
    filters = [
        f'{symbol} /{p}**' for p in paths
    ]
    return filters


import os
def parse_paths2(anchor_root, paths):
    struct_list = [{anchor_root: paths}]
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
                            new_item = os.path.join(root, item)
                        else:
                            finished = False
                            new_item = {
                                os.path.join(root, subroot):
                                    subitems for subroot, subitems in item.items()
                            }
                        new_struct_list.append(new_item)

        struct_list = new_struct_list

    paths = struct_list
    subpaths = [p.replace(anchor_root + "/", "") for p in paths]
    return paths, subpaths
