import hmac
import hashlib
from functools import wraps
from flask import request, session, redirect, url_for, jsonify
from config.settings import Config
from utils.logger import get_logger

logger = get_logger("security")

def verify_control_secret(secret: str) -> bool:
    return hmac.compare_digest(
        secret.encode("utf-8"),
        Config.CONTROL_SECRET.encode("utf-8")
    )

def require_admin(f):
    """Require session-based admin authentication."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect("/admin/login")
        return f(*args, **kwargs)
    return decorated

def require_api_secret(f):
    """Require secret in JSON body for API endpoints."""
    @wraps(f)
    def decorated(*args, **kwargs):
        data = request.get_json(silent=True) or {}
        secret = data.get("secret", "")
        if not verify_control_secret(secret):
            logger.warning(f"Unauthorized API access from {request.remote_addr}")
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated
