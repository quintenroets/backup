from __future__ import annotations

import typing
from dataclasses import dataclass, field
from typing import Any

from typing_extensions import Self

from backup.models import Entries, Path, PathRule

if typing.TYPE_CHECKING:
    from collections.abc import Iterator  # pragma: nocover


@dataclass
class RuleConfig:
    items: list[str] = field(default_factory=list)
    sub_rules: dict[str, RuleConfig] = field(default_factory=dict)
    path_separator: str = field(repr=False, default="/")
    VERSION_KEYWORD: str = field(repr=False, default="__VERSION__")

    @classmethod
    def from_list(cls, items: Entries, root: Path) -> Self:
        rules = cls()
        if items is not None:
            for item in items:
                rules.add_item(item, root)
        return rules

    def add_item(
        self,
        item: dict[Any, Any] | str | tuple[str, ...],
        root: Path,
    ) -> None:
        names, content = (
            next(iter(item.items())) if isinstance(item, dict) else (item, [])
        )
        if isinstance(names, str):
            full_path = root / names
            path = full_path.resolve()
            if not path.is_relative_to(root):  # pragma: no cover
                message = "Currently, only symlinks under the same sub root are allowed"
                raise ValueError(message)
            names = str(path.relative_to(root))
            names = names.split(RuleConfig.path_separator)

        name, *sub_names = names
        name = self.parse_name(name, root)
        if sub_names:
            content = [{tuple(sub_names): content}]
        if content:
            self.sub_rules[name] = RuleConfig.from_list(content, root=root / name)
        else:
            self.items.append(name)

    @classmethod
    def parse_name(cls, name: str, root: Path) -> str:
        if cls.VERSION_KEYWORD in name:
            name_start = name.split(cls.VERSION_KEYWORD)[0]
            true_paths = list(root.glob(f"{name_start}*"))
            true_paths = sorted(true_paths, key=lambda path: -path.mtime)
            name = true_paths[0].name if true_paths else "__NON_EXISTING__"
        return name


@dataclass
class RuleParser:
    root: Path
    sub_path: Path = field(default_factory=lambda: Path(""))
    includes: Entries = field(default_factory=list)
    excludes: Entries = field(default_factory=list)

    def parse_rules(self) -> list[PathRule]:
        return list(self.parse())

    def get_paths(self) -> Iterator[Path]:
        for rule in self.parse():
            yield rule.path

    def parse(self) -> Iterator[PathRule]:
        include_rules = RuleConfig.from_list(self.includes, self.root)
        exclude_rules = RuleConfig.from_list(self.excludes, self.root)
        parent_seen = False
        for rule in self.generate_rules(include_rules, exclude_rules):
            if rule.path.is_relative_to(self.sub_path):
                yield PathRule(rule.path.relative_to(self.sub_path), rule.include)
            elif self.sub_path.is_relative_to(rule.path) and not parent_seen:
                parent_seen = True
                yield PathRule(Path(), include=rule.include)
        if not parent_seen:
            yield PathRule(Path(), include=False)

    def generate_rules(
        self,
        include: RuleConfig,
        exclude: RuleConfig,
    ) -> Iterator[PathRule]:
        sub_names = include.sub_rules.keys() | exclude.sub_rules.keys()
        for name in sub_names:
            sub_include = include.sub_rules.get(name, RuleConfig())
            sub_exclude = exclude.sub_rules.get(name, RuleConfig())
            for rule in self.generate_rules(sub_include, sub_exclude):
                path = Path(name) / rule.path
                yield PathRule(path, rule.include)

        yield from self.extract_rules(include, include=True)
        yield from self.extract_rules(exclude, include=False)

    def extract_rules(self, config: RuleConfig, *, include: bool) -> Iterator[PathRule]:
        for name in config.items:
            yield PathRule(Path(name), include)
