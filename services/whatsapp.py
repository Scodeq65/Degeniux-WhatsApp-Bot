import requests
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("whatsapp")

BASE_URL = f"https://graph.facebook.com/{Config.GRAPH_API_VERSION}/{Config.PHONE_NUMBER_ID}"
HEADERS = {
    "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
    "Content-Type": "application/json"
}

MEDIA_RESPONSES = {
    "image":    "Thanks for sending that! Kindly type out what you need and I'll assist you right away. 😊",
    "audio":    "Hey! I noticed you sent a voice note. Kindly type your message and I'll help immediately. 😊",
    "video":    "Thanks for that! Kindly type your request and I'll be happy to assist. 😊",
    "document": "Thanks for sending that document! Our team will review it. Anything else I can help you with?",
    "sticker":  "😊 Kindly type your message so I can assist you properly.",
}


def send_text(to: str, message: str) -> bool:
    try:
        r = requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            json={
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": message, "preview_url": False}
            },
            timeout=10
        )
        logger.info(f"WhatsApp send to +{to}: {r.status_code}")
        if r.status_code != 200:
            logger.error(f"WhatsApp error response: {r.text}")
        return r.status_code == 200
    except requests.Timeout:
        logger.error(f"WhatsApp timeout for +{to}")
        return False
    except Exception as e:
        logger.error(f"WhatsApp send error: {e}")
        return False


def send_template(to: str, template_name: str, params: list = None) -> bool:
    try:
        components = []
        if params:
            components.append({
                "type": "body",
                "parameters": [{"type": "text", "text": str(p)} for p in params]
            })
        r = requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": components
                }
            },
            timeout=10
        )
        logger.info(f"Template '{template_name}' to +{to}: {r.status_code}")
        return r.status_code == 200
    except Exception as e:
        logger.error(f"Template error: {e}")
        return False


def mark_read(message_id: str):
    try:
        requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            json={"messaging_product": "whatsapp", "status": "read", "message_id": message_id},
            timeout=5
        )
    except Exception as e:
        logger.error(f"Mark read error: {e}")


def handle_media(to: str, media_type: str) -> bool:
    msg = MEDIA_RESPONSES.get(media_type, "Hey! Kindly type your message and I'll be happy to help. 😊")
    return send_text(to, msg)
