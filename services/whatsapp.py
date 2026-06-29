import requests
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("whatsapp")


class WhatsAppService:
    """Centralized WhatsApp Cloud API service layer."""

    BASE_URL = f"{Config.WHATSAPP_API_URL}/{Config.PHONE_NUMBER_ID}"

    HEADERS = {
        "Authorization": f"Bearer {Config.WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    @classmethod
    def send_text(cls, to: str, message: str) -> bool:
        """Send a plain text message."""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "recipient_type": "individual",
                "to": to,
                "type": "text",
                "text": {"body": message, "preview_url": False}
            }
            response = requests.post(
                f"{cls.BASE_URL}/messages",
                headers=cls.HEADERS,
                json=payload,
                timeout=10
            )
            logger.info(f"WhatsApp send to {to}: {response.status_code}")
            if response.status_code != 200:
                logger.error(f"WhatsApp error: {response.text}")
                return False
            return True
        except requests.Timeout:
            logger.error(f"WhatsApp timeout for {to}")
            return False
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            return False

    @classmethod
    def send_template(cls, to: str, template_name: str, params: list = None) -> bool:
        """Send an approved WhatsApp template message."""
        try:
            components = []
            if params:
                components.append({
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": str(p)} for p in params
                    ]
                })

            payload = {
                "messaging_product": "whatsapp",
                "to": to,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": "en"},
                    "components": components
                }
            }
            response = requests.post(
                f"{cls.BASE_URL}/messages",
                headers=cls.HEADERS,
                json=payload,
                timeout=10
            )
            logger.info(f"Template '{template_name}' to {to}: {response.status_code}")
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Template send error: {e}")
            return False

    @classmethod
    def mark_read(cls, message_id: str):
        """Mark a message as read."""
        try:
            payload = {
                "messaging_product": "whatsapp",
                "status": "read",
                "message_id": message_id
            }
            requests.post(
                f"{cls.BASE_URL}/messages",
                headers=cls.HEADERS,
                json=payload,
                timeout=5
            )
        except Exception as e:
            logger.error(f"Mark read error: {e}")

    @classmethod
    def handle_media_message(cls, to: str, media_type: str) -> bool:
        """Handle non-text message types gracefully."""
        responses = {
            "image": "Thanks for sending that! For registration purposes, kindly type out the details you need help with and I'll assist you right away. 😊",
            "audio": "Hey! I noticed you sent a voice note. Kindly type out what you need and I'll help you immediately. 😊",
            "video": "Thanks for that! Kindly type out your request and I'll be happy to assist. 😊",
            "document": "Thanks for sending that document! Our team will review it shortly. Is there anything else I can help you with?",
            "sticker": "😊 Kindly type your message so I can assist you properly.",
        }
        message = responses.get(
            media_type,
            "Hey! Kindly type your message and I'll be happy to help. 😊"
        )
        return cls.send_text(to, message)

    @classmethod
    def is_within_24h_window(cls, last_customer_message_at) -> bool:
        """Check if we're within the 24-hour service window."""
        from datetime import datetime, timedelta
        if not last_customer_message_at:
            return False
        return datetime.utcnow() - last_customer_message_at < timedelta(hours=24)
