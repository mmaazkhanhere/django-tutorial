import re

def extract_name_and_email(sender_string):
    """
    Extracts both the name and email address from a string like:
    'Name <email@example.com>'.
    Returns (name, email) tuple.
    """
    match = re.match(r'(?:"?([^"]*)"?\s)?<?([^<>]+@[^<>]+)>?', sender_string)
    if match:
        name = match.group(1).strip() if match.group(1) else ''
        email = match.group(2).strip()
        return name, email
    return '', sender_string  # If no brackets, return empty name and raw string as email