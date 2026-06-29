import re

def is_valid_email(text: str) -> bool:
    pattern = r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, text.strip()))

def is_valid_phone(text: str) -> bool:
    digits = re.sub(r'\D', '', text)
    return 10 <= len(digits) <= 15

def clean_phone(text: str) -> str:
    digits = re.sub(r'\D', '', text)
    if digits.startswith('0') and len(digits) == 11:
        return '234' + digits[1:]
    return digits

def extract_email(text: str) -> str:
    pattern = r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}'
    match = re.search(pattern, text)
    return match.group(0) if match else ""

def sanitize_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
