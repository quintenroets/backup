def create_malformed_filters_error(filters):
    delimiter = "\n\t"
    malformed_rules = generate_malformed_rules(filters)
    message = f"Invalid paths:{delimiter}" + delimiter.join(malformed_rules)
    return Exception(message)


def generate_malformed_rules(filters):
    invalid_characters = ("\n",)
    for rule in filters:
        if any(character in rule for character in invalid_characters):
            path = rule[3:]
            raw_path = path.encode("unicode_escape").decode()
            yield raw_path
