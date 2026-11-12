from dataclasses import dataclass, field

from superpathlib import Path


@dataclass
class SyncConfig:
    source: Path
    dest: Path
    filter_rules: list[str] = field(default_factory=list)
    paths: list[Path] = field(default_factory=list)
