from collections.abc import Iterator

from backup.backup.paths import reserved_characters


def create_malformed_filters_error(filters: list[str]) -> Exception:
    delimiter = "\n\t"
    malformed_rules = generate_malformed_rules(filters)
    message = f"Invalid paths:{delimiter}" + delimiter.join(malformed_rules)
    return ValueError(message)


def generate_malformed_rules(filters: list[str]) -> Iterator[str]:
    for rule in filters:
        if any(character in rule for character in reserved_characters):
            path = rule[3:]
            raw_path = path.encode("unicode_escape").decode()
            yield raw_path
