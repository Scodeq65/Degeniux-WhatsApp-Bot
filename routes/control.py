from flask import Blueprint, request, jsonify
from workflow.fsm import ConversationFSM
from workflow.states import State
from services.notification import notify_bot_paused, notify_bot_resumed
from utils.security import require_secret
from utils.logger import get_logger

control_bp = Blueprint("control", __name__)
logger = get_logger("control")


@control_bp.route("/control", methods=["POST"])
@require_secret
def control():
    data = request.get_json(silent=True) or {}
    command = data.get("command", "").upper()
    phone = data.get("user_id", "").strip()

    if not phone:
        return jsonify({"error": "user_id (phone) required"}), 400

    fsm = ConversationFSM(phone)

    if command == "PAUSE":
        fsm.pause()
        notify_bot_paused(phone)
        logger.info(f"Bot PAUSED for +{phone}")
        return jsonify({"status": f"Bot paused for +{phone}. You can now handle manually."}), 200

    elif command == "RESUME":
        fsm.resume()
        notify_bot_resumed(phone)
        logger.info(f"Bot RESUMED for +{phone}")
        return jsonify({"status": f"Bot resumed for +{phone}. AI is active again."}), 200

    elif command == "STATUS":
        return jsonify({
            "phone": phone,
            "state": fsm.state.value,
            "paused": fsm.is_paused(),
            "collected": fsm.collected
        }), 200

    elif command == "RESET":
        fsm.transition(State.GREETING_SENT)
        fsm.resume()
        return jsonify({"status": f"Conversation reset for +{phone}"}), 200

    return jsonify({"error": "Invalid command. Use: PAUSE, RESUME, STATUS, RESET"}), 400
