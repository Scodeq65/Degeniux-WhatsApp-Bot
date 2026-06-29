import hashlib
import hmac
import time
from functools import wraps
from flask import request, jsonify
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("security")

def verify_control_secret(secret: str) -> bool:
    return hmac.compare_digest(secret, Config.CONTROL_SECRET)

def require_secret(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        secret = request.args.get("secret") or (
            request.get_json(silent=True) or {}
        ).get("secret", "")
        if not verify_control_secret(secret):
            logger.warning(f"Unauthorized access attempt from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated

def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    app_secret = Config.WHATSAPP_TOKEN
    if not app_secret or not signature:
        return True  # Skip in dev
    try:
        expected = hmac.new(
            app_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(f"sha256={expected}", signature)
    except Exception:
        return False
