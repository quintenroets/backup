from collections.abc import Iterator, Sequence

from superpathlib import Path

from .models import PathRule
from .sync_config import SyncConfig

reserved_characters = "\\", "[", "]", "*", "**", "?", "{", "}"
path_separator = "/"
recursive_symbol = "**"


def generate_filters(config: SyncConfig) -> Iterator[str]:
    if config.filter_rules:
        yield from config.filter_rules
    elif config.rules:
        yield from generate_rule_filters(config.rules)
    else:
        yield from generate_path_filters(config)


def generate_rule_filters(rules: list[PathRule]) -> Iterator[str]:
    for rule in rules:
        yield from expand_rule(rule)
    yield "- *"


def expand_rule(rule: PathRule) -> Iterator[str]:
    sign = "+" if rule.include else "-"
    if rule.depth:
        path = escape(rule.path)
        yield f"{sign} /{path}"
        yield f"{sign} /{path}/**"
    else:
        yield f"{sign} /**"


def generate_path_filters(config: SyncConfig) -> Iterator[str]:
    paths = resolve_paths(config)
    for path in paths:
        relative_path = (
            path.relative_to(config.source)
            if path.is_relative_to(config.source)
            else path
        )
        yield f"+ /{escape(relative_path)}"

    if paths:
        yield "- *"


def resolve_paths(config: SyncConfig) -> Sequence[Path]:
    return (
        (config.directory / recursive_symbol,)
        if config.directory is not None
        else (config.path,)
        if config.path is not None
        else config.paths
    )


def escape(path: Path) -> str:
    recursive = path.name == recursive_symbol
    if recursive:
        path = path.parent
    path_str = path_separator.join(path.parts)
    for character in reserved_characters:
        path_str = path_str.replace(character, f"\\{character}")
    if recursive:
        path_str += path_separator + recursive_symbol

    return path_str
