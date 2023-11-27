from dataclasses import dataclass, field
from typing import Any

import cli

from ....utils import Path


@dataclass
class PathChecker:
    ignore_sections: tuple[str, ...] = field(default_factory=list)
    ignore_lines: tuple[str, ...] = field(default_factory=list)

    def __post_init__(self):
        self.ignore_sections_str = [f"[{section}]" for section in self.ignore_sections]

    def calculate_relevant_hash(self, path: Path):
        content = self.get_content(path) if path.exists() else None
        return hash(content)

    def get_content(self, path: Path) -> Any:
        content = self.generate_content(path)
        return tuple(content)

    def generate_content(self, path: Path):
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
    ignore_lines: tuple[str, ...] = field(default_factory=lambda: ["#"])


class UserPlaceChecker(PathChecker):
    tag_ignore_names: tuple[str, ...] = ("tags", "kdeconnect")

    def get_content(self, path: Path) -> Any:
        tags = self.generate_tags(path)
        return tuple(tags)

    def generate_tags(self, path: Path) -> Any:
        from bs4 import BeautifulSoup  # noqa: E402, autoimport

        soup = BeautifulSoup(path.text, features="xml")
        for tag in soup.find_all("bookmark"):
            href = tag.get("href")
            if not any([name in href for name in self.tag_ignore_names]):
                yield str(tag)


class RetrievedContentChecker(PathChecker):
    def get_content(self, path: Path) -> Any:
        hash_path = path.hash_path
        # compare generated hash with saved hash
        content_hash = (
            hash_path.text
            if hash_path.is_relative_to(Path.backup_cache)
            else self.calculate_content_hash()
        )
        if content_hash != hash_path.text:
            hash_path.text = content_hash
        return content_hash

    def calculate_content_hash(self):
        import hashlib  # noqa: E402, autoimport
        import json  # noqa: E402, autoimport

        content = self.retrieve_content()
        content_bytes = json.dumps(content).encode()
        hash_value = hashlib.new("sha512", data=content_bytes).hexdigest()
        return hash_value

    def retrieve_content(self):
        raise NotImplementedError


class KwalletChecker(RetrievedContentChecker):
    def retrieve_content(self):
        folders = ("Network Management", "Passwords", "ksshaskpass")
        with cli.status("Checking kwallet content"):
            info = {folder: self.calculate_folder_info(folder) for folder in folders}
        return info

    @classmethod
    def calculate_folder_info(cls, folder) -> dict[str, str]:
        try:
            items = cli.lines("kwallet-query -l kdewallet -f", folder)
        except cli.CalledProcessError:
            items = []
        return {
            item: cli.get("kwallet-query kdewallet -r", item, "-f", folder)
            for item in items
        }


class RcloneChecker(RetrievedContentChecker):
    def retrieve_content(self):
        config_lines = cli.lines("rclone config show")
        nonvolatile_config_lines = [
            line for line in config_lines if "refresh_token" not in line
        ]
        return nonvolatile_config_lines
