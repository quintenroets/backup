from __future__ import annotations

from dataclasses import dataclass, field

from .path import Path


@dataclass
class PathRule:
    path: Path
    include: bool


@dataclass
class RuleConfig:
    items: list[str] = field(default_factory=list)
    sub_rules: dict[str, RuleConfig] = field(default_factory=dict)
    path_separator: str = field(repr=False, default="/")
    VERSION_KEYWORD: str = field(repr=False, default="__VERSION__")

    @classmethod
    def from_list(cls, items: list | None, root: Path):
        rules = RuleConfig()
        if items is not None:
            for item in items:
                rules.add_item(item, root)
        return rules

    def add_item(self, item: dict | str | tuple, root: Path):
        names, content = (
            next(iter(item.items())) if isinstance(item, dict) else (item, [])
        )
        if isinstance(names, str):
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
    def parse_name(cls, name: str, root: Path):
        if name == "HOME":
            name = str(Path.HOME.relative_to(root))
        if cls.VERSION_KEYWORD in name:
            name_start = name.split(cls.VERSION_KEYWORD)[0]
            true_paths = list(root.glob(f"{name_start}*"))
            true_paths = sorted(true_paths, key=lambda path: -path.mtime)
            name = true_paths[0].name
        return name


@dataclass
class Rules:
    include_rules: list | None = None
    exclude_rules: list | None = None
    root: Path = Path()

    def __iter__(self):
        yield from self.parse()

    def get_paths(self):
        for rule in self.parse():
            yield rule.path

    def parse(self):
        include_rules = RuleConfig.from_list(self.include_rules, self.root)
        exclude_rules = RuleConfig.from_list(self.exclude_rules, self.root)
        yield from self.generate_rules(include_rules, exclude_rules)

    def generate_rules(self, include: RuleConfig, exclude: RuleConfig):
        sub_names = include.sub_rules.keys() | exclude.sub_rules.keys()
        for name in sub_names:
            sub_include = include.sub_rules.get(name, RuleConfig())
            sub_exclude = exclude.sub_rules.get(name, RuleConfig())
            for rule in self.generate_rules(sub_include, sub_exclude):
                path = Path(name) / rule.path
                yield PathRule(path, rule.include)

        rules_dict = {True: include, False: exclude}
        for include, rules in rules_dict.items():
            for name in rules.items:
                path = Path(name)
                yield PathRule(path, include)
