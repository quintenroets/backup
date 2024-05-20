import os
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

import cli

from ....context import context
from ....models import Path


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
        content_lines = path.lines
        header_indices = [
            i for i, line in enumerate(content_lines) if line.startswith("[")
        ]
        non_volatile_sections = []
        for start, end in zip(header_indices, header_indices[1:]):
            section = content_lines[start:end]
            if section[0] not in self.ignore_sections_str:
                non_volatile_sections.append(section)

        for section in non_volatile_sections:
            for line in section:
                if not any(word in line for word in self.ignore_lines):
                    yield line


class CommentsRemovedChecker(PathChecker):
    ignore_lines: tuple[str, ...] = ("#",)


class UserPlaceChecker(PathChecker):
    tag_ignore_names: tuple[str, ...] = ("tags", "kdeconnect")

    def extract_content(self, path: Path) -> Iterator[str]:
        from bs4 import BeautifulSoup  # noqa: E402, autoimport

        soup = BeautifulSoup(path.text, features="xml")
        for tag in soup.find_all("bookmark"):
            href = tag.get("href")
            if not any([name in href for name in self.tag_ignore_names]):
                yield str(tag)


class RetrievedContentChecker(PathChecker):
    def extract_content(self, path: Path) -> Iterator[str]:
        hash_path = path.hash_path
        # compare generated hash with saved hash
        content_hash = (
            hash_path.text
            if hash_path.is_relative_to(Path.backup_cache)
            else self.calculate_content_hash()
        )
        if content_hash != hash_path.text:
            hash_path.text = content_hash
        yield content_hash

    def calculate_content_hash(self) -> str:
        import hashlib  # noqa: E402, autoimport
        import json  # noqa: E402, autoimport

        content_generator = self.retrieve_content()
        content = tuple(content_generator)
        content_bytes = json.dumps(content).encode()
        hash_value = hashlib.new("sha512", data=content_bytes).hexdigest()
        return hash_value

    def retrieve_content(self) -> Any:
        raise NotImplementedError


class KwalletChecker(RetrievedContentChecker):
    def retrieve_content(
        self,
    ) -> Iterator[tuple[str, tuple[tuple[str, list[str]], ...]]]:
        folders = ("Network Management", "Passwords", "ksshaskpass")
        with cli.status("Checking kwallet content"):
            for folder in folders:
                info = self.calculate_folder_info(folder)
                yield folder, tuple(info)

    @classmethod
    def calculate_folder_info(cls, folder: str) -> Iterator[tuple[str, list[str]]]:
        try:
            items = cli.capture_output_lines("kwallet-query -l kdewallet -f", folder)
            command = "kwallet-query kdewallet -r"
            for item in items:
                yield item, cli.capture_output_lines(command, item, "-f", folder)
        except cli.CalledProcessError:
            pass


class RcloneChecker(RetrievedContentChecker):
    def retrieve_content(self) -> Iterator[str]:
        env = os.environ | {"RCLONE_CONFIG_PASS": context.secrets.rclone}
        lines = cli.capture_output_lines("rclone config show", env=env)
        for line in lines:
            if "refresh_token" not in line:
                yield line
