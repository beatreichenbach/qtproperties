import re


def title(text):
    text = re.sub(r'([a-z0-9])([A-Z])', r'\1 \2', text).replace('_', ' ').title()
    return text
