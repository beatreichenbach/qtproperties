import re


def title(text):
    text = re.sub(r'(\w)([A-Z])', r'\1 \2', text).replace('_', ' ').title()
    return text
