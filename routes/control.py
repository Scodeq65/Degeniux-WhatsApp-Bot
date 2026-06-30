from flask import Blueprint, request, jsonify
from database.models import get_customer, ensure_customer, update_conversation
from workflow.fsm import FSM
from workflow.states import State
from services.notification import notify_bot_paused, notify_bot_resumed
from utils.security import require_api_secret
from utils.logger import get_logger

control_bp = Blueprint("control", __name__)
logger = get_logger("control")


@control_bp.route("/admin/control", methods=["POST"])
@require_api_secret
def control():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").upper().strip()
    phone = data.get("user_id", "").strip()

    if not phone:
        return jsonify({"error": "user_id required"}), 400

    ensure_customer(phone)
    customer = get_customer(phone)
    fsm = FSM(phone, customer)

    if command == "PAUSE":
        fsm.pause()
        notify_bot_paused(phone)
        return jsonify({"status": f"Bot paused for +{phone}"}), 200

    elif command == "RESUME":
        fsm.resume()
        notify_bot_resumed(phone)
        return jsonify({"status": f"Bot resumed for +{phone}"}), 200

    elif command == "STATUS":
        return jsonify({
            "phone": phone,
            "state": fsm.state.value,
            "paused": fsm.is_paused(),
            "collected": fsm.collected
        }), 200

    elif command == "RESET":
        fsm.resume()
        update_conversation(phone, fsm_state=State.GREETING_SENT.value)
        return jsonify({"status": f"Conversation reset for +{phone}"}), 200

    return jsonify({"error": "Use: PAUSE, RESUME, STATUS, RESET"}), 400
