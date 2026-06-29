import os

class Config:
    # Claude
    CLAUDE_API_KEY = os.environ.get("CLAUDE_API_KEY")
    CLAUDE_MODEL = "claude-sonnet-4-6"
    CLAUDE_MAX_TOKENS = 600

    # WhatsApp
    WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
    PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
    VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "degenius2024")
    GRAPH_API_VERSION = "v25.0"

    # Database
    DATABASE_URL = os.environ.get("DATABASE_URL")
    DB_POOL_MIN = 1
    DB_POOL_MAX = 5

    # Telegram
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "-1003702145774")

    # App
    RENDER_URL = os.environ.get("RENDER_URL", "https://degeniux-whatsapp-bot.onrender.com")
    CONTROL_SECRET = os.environ.get("CONTROL_SECRET", "degenius_control_2024")
    FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "degenius_flask_2024")

    # Scheduler
    FOLLOWUP_HOURS = 24
    REPORT_HOUR = 7
    MAX_FOLLOWUPS = 3

    # Knowledge base path
    KNOWLEDGE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "knowledge")
