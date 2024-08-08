import itertools
import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, cast

import cli

from backup.context import context
from backup.models import Path


def extract_hash_path(path: Path) -> Path:
    root = (
        context.config.cache_path
        if path.is_relative_to(context.config.cache_path)
        else context.config.backup_source
    )
    relative_hashes = cast(Path, Path.hashes).relative_to(Path.backup_source)
    return root / relative_hashes / path.name


@dataclass
class PathChecker:
    ignore_sections: tuple[str, ...] = ()
    ignore_lines: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        self.ignore_sections_str = [f"[{section}]" for section in self.ignore_sections]

    def calculate_relevant_hash(self, path: Path) -> int:
        if path.exists():
            content_items = self.extract_content(path)
            content = tuple(content_items)
        else:
            content = None
        return hash(content)

    def extract_content(self, path: Path) -> Iterator[str]:
        for section in self.extract_sections(path):
            if section[0] not in self.ignore_sections_str:
                for line in section:
                    if not any(word in line for word in self.ignore_lines):
                        yield line

    @classmethod
    def extract_sections(cls, path: Path) -> Iterator[list[str]]:
        content_lines = path.lines
        header_indices = [
            i for i, line in enumerate(content_lines) if line.startswith("[")
        ]
        header_indices.append(len(content_lines))
        for start, end in itertools.pairwise(header_indices):
            yield content_lines[start:end]


class CommentsRemovedChecker(PathChecker):
    ignore_lines: tuple[str, ...] = ("#",)


class UserPlaceChecker(PathChecker):
    tag_ignore_names: tuple[str, ...] = ("tags", "kdeconnect")

    def extract_content(self, path: Path) -> Iterator[str]:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(path.text, features="xml")
        for tag in soup.find_all("bookmark"):
            href = tag.get("href")
            if not any(name in href for name in self.tag_ignore_names):
                yield str(tag)


class RetrievedContentChecker(PathChecker):
    def extract_content(self, path: Path) -> Iterator[str]:
        hash_path = extract_hash_path(path)
        # compare generated hash with saved hash
        content_hash = (
            hash_path.text
            if hash_path.is_relative_to(context.config.cache_path)
            else self.calculate_content_hash()
        )
        if content_hash != hash_path.text:
            hash_path.text = content_hash
        yield content_hash

    def calculate_content_hash(self) -> str:
        import hashlib
        import json

        content_generator = self.retrieve_content()
        content = tuple(content_generator)
        content_bytes = json.dumps(content).encode()
        return hashlib.new("sha512", data=content_bytes).hexdigest()

    def retrieve_content(self) -> Any:
        raise NotImplementedError  # pragma: nocover


@dataclass
class KwalletItem:
    folder: str
    item: str


class KwalletChecker(RetrievedContentChecker):
    def retrieve_content(self) -> Iterator[tuple[str, str, list[str]]]:
        items = list(self.generate_items())
        items_with_progress = cli.track_progress(
            items,
            description="Checking kwallet content",
            unit="items",
        )
        command = "kwallet-query kdewallet -r"
        for item in items_with_progress:
            full_command = command, item.item, "-f", item.folder
            info = cli.capture_output_lines(*full_command)
            yield item.folder, item.item, info

    @classmethod
    def generate_items(cls) -> Iterator[KwalletItem]:
        folders = ("Network Management", "Passwords", "ksshaskpass")
        command = "kwallet-query -l kdewallet -f"
        for folder in folders:
            for item in cli.capture_output_lines(command, folder):
                yield KwalletItem(folder=folder, item=item)


class RcloneChecker(RetrievedContentChecker):
    def retrieve_content(self) -> Iterator[str]:
        env = os.environ | {"RCLONE_CONFIG_PASS": context.secrets.rclone}
        lines = cli.capture_output_lines("rclone config show", env=env)
        for line in lines:
            if "refresh_token" not in line:
                yield line
