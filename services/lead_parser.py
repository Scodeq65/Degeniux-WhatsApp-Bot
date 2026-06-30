import re
from utils.logger import get_logger
from config.business_loader import identify_service

logger = get_logger("lead_parser")


def parse_from_message(message: str, current_state: str, collected: dict) -> dict:
    """
    Extract structured data from a user message.
    Returns dict of extracted fields.
    """
    extracted = {"raw_message": message}
    text = message.strip()

    # Extract name — look for patterns like "my name is X" or "I am X"
    name_match = re.search(
        r"(?:my name is|i am|i'm|call me|this is)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,2})",
        text, re.IGNORECASE
    )
    if name_match and not collected.get("customer_name"):
        extracted["customer_name"] = name_match.group(1).strip()

    # Extract service if not yet identified
    if not collected.get("service_requested"):
        detected = identify_service(text)
        if detected:
            extracted["service"] = detected

    # Extract business name — look for quoted text or "called/named X"
    if not collected.get("proposed_business_name") and current_state in [
        "WAITING_BUSINESS_NAME", "SERVICE_IDENTIFIED", "BUSINESS_NAME_RECEIVED"
    ]:
        # Quoted name
        quoted = re.search(r'["\u201c\u201d]([^""\u201c\u201d]{3,80})["\u201c\u201d]', text)
        if quoted:
            extracted["business_name"] = quoted.group(1).strip()
        # Named/called pattern
        elif re.search(r"(?:called|named|name is|going with|prefer)\s+(.+)", text, re.IGNORECASE):
            match = re.search(r"(?:called|named|name is|going with|prefer)\s+(.+)", text, re.IGNORECASE)
            candidate = match.group(1).strip()
            if len(candidate) > 2 and not any(
                w in candidate.lower() for w in ["register", "help", "want", "need"]
            ):
                extracted["business_name"] = candidate

    # Extract nature of business
    if not collected.get("nature_of_business") and current_state == "WAITING_NATURE":
        if len(text) > 5:
            extracted["nature"] = text

    logger.info(f"Parsed from message: {extracted}")
    return extracted
