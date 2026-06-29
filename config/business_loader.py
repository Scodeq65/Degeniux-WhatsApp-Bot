import json
import os
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("business_loader")

_cache = {}

def load(filename: str) -> dict:
    global _cache
    if filename in _cache:
        return _cache[filename]
    try:
        path = os.path.join(Config.KNOWLEDGE_PATH, filename)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache[filename] = data
        logger.info(f"Loaded knowledge file: {filename}")
        return data
    except FileNotFoundError:
        logger.error(f"Knowledge file not found: {filename}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"JSON error in {filename}: {e}")
        return {}

def get_business() -> dict:
    return load("business.json")

def get_pricing() -> dict:
    return load("pricing.json")

def get_services() -> dict:
    return load("services.json")

def get_requirements() -> dict:
    return load("requirements.json")

def get_objections() -> dict:
    return load("objections.json")

def get_faqs() -> dict:
    return load("faqs.json")

def format_requirements(service_key: str) -> str:
    reqs = get_requirements()
    if service_key not in reqs:
        return ""
    data = reqs[service_key]
    lines = [data["intro"], ""]
    for section in data.get("sections", []):
        lines.append(f"*{section['title']}*")
        for item in section["items"]:
            lines.append(f"• {item}")
        lines.append("")
    return "\n".join(lines).strip()

def format_pricing(service_key: str) -> str:
    pricing = get_pricing()
    if service_key not in pricing:
        return ""
    p = pricing[service_key]
    symbol = p.get("symbol", "₦")
    amount = p.get("amount")
    if not amount:
        return p.get("note", "Pricing varies. Please describe what you need.")
    stages = p.get("stages", {})
    lines = [
        f"*{p['label']}*",
        f"Fee: {symbol}{amount:,}",
        f"Timeline: {p['timeline']}",
        "",
        "*Payment Structure:*"
    ]
    for stage_key in sorted(stages.keys()):
        s = stages[stage_key]
        lines.append(f"• Stage {stage_key[-1]}: {symbol}{s['amount']:,} ({s['percent']}%)")
    return "\n".join(lines)

def identify_service(text: str) -> str:
    services = get_services()
    text_lower = text.lower()
    for svc in services.get("registration", []):
        for alias in svc.get("aliases", []):
            if alias in text_lower:
                return svc["key"]
    for post in services.get("post_registration", []):
        if post in text_lower:
            return "post_registration"
    return ""
