import requests
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("telegram")


def send(text: str, parse_mode: str = "HTML") -> bool:
    token = Config.TELEGRAM_BOT_TOKEN
    chat_id = Config.TELEGRAM_CHAT_ID

    if not token or not chat_id:
        logger.warning("Telegram not configured — TOKEN or CHAT_ID missing.")
        return False

    logger.info(f"Sending Telegram to chat_id={chat_id}")

    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }
        r = requests.post(url, json=payload, timeout=15)
        logger.info(f"Telegram response: {r.status_code} — {r.text[:300]}")

        if r.status_code != 200:
            error_data = r.json()
            logger.error(f"Telegram API error: {error_data.get('description', 'Unknown error')}")
            # Common fixes
            if "chat not found" in r.text.lower():
                logger.error("Chat ID not found. Ensure bot is added to group as admin.")
            if "bot was kicked" in r.text.lower():
                logger.error("Bot was removed from group. Re-add as admin.")
            return False

        return True

    except requests.Timeout:
        logger.error("Telegram request timed out.")
        return False
    except Exception as e:
        logger.error(f"Telegram send error: {e}")
        return False
