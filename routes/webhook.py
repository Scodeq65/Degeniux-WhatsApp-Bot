import json
from flask import Blueprint, request
from database.models import (
    ensure_customer, get_customer, save_message,
    get_recent_messages, update_customer, log_activity
)
from workflow.fsm import FSM
from workflow.handover import trigger_handover
from workflow.states import State
from services.whatsapp import send_text, mark_read, handle_media
from services.claude_service import get_response
from services.lead_parser import parse_from_message
from services.notification import notify_new_lead, notify_lead_qualified
from config.settings import Config
from utils.logger import get_logger

webhook_bp = Blueprint("webhook", __name__)
logger = get_logger("webhook")


@webhook_bp.route("/webhook", methods=["GET"])
def verify():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == Config.VERIFY_TOKEN:
        logger.info("Webhook verified.")
        return challenge, 200
    logger.warning("Webhook verification failed.")
    return "Forbidden", 403


@webhook_bp.route("/webhook", methods=["POST"])
def receive():
    data = request.get_json()
    logger.info(f"Webhook: {json.dumps(data)[:400]}")

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Ignore status updates
        if "statuses" in value and "messages" not in value:
            return "OK", 200

        if "messages" not in value:
            return "OK", 200

        msg = value["messages"][0]
        phone = msg["from"]
        msg_type = msg.get("type", "")
        msg_id = msg.get("id", "")

        logger.info(f"From +{phone} | Type: {msg_type}")

        # Mark read
        if msg_id:
            mark_read(msg_id)

        # Handle non-text
        if msg_type != "text":
            handle_media(phone, msg_type)
            return "OK", 200

        user_message = msg["text"]["body"].strip()
        if not user_message:
            return "OK", 200

        # Ensure records exist
        ensure_customer(phone)

        # Load customer state
        customer = get_customer(phone)
        fsm = FSM(phone, customer)

        # Skip if bot is paused
        if fsm.is_paused():
            logger.info(f"Bot paused for +{phone} — skipping.")
            return "OK", 200

        # Update last message timestamp
        update_customer(phone, last_message_at="CURRENT_TIMESTAMP")

        # Notify on first message
        if not customer.get("notified_new"):
            notify_new_lead(phone)
            from database.models import update_conversation
            update_conversation(phone, notified_new=True)

        # Save incoming message
        save_message(phone, "user", user_message, fsm.state.value)

        # Quick parse for obvious extractions
        quick_extracted = parse_from_message(
            user_message,
            fsm.state.value,
            fsm.collected
        )

        # Get recent messages for Claude context
        recent = get_recent_messages(phone, limit=8)

        # Get Claude response
        service_key = fsm.collected.get("service_requested", "")
        claude_data = get_response(
            phone=phone,
            user_message=user_message,
            state=fsm.state,
            instruction=fsm.get_instruction(),
            collected=fsm.collected,
            recent_messages=recent[:-1] if recent else [],
            service_key=service_key
        )

        # Merge extracted data
        combined = {**quick_extracted}
        claude_customer = claude_data.get("customer_data", {})
        for k, v in claude_customer.items():
            if v and k not in combined:
                combined[k] = v

        # Advance FSM
        fsm.process_extracted(combined)

        # Extract and send reply
        reply = (claude_data.get("reply") or "").strip()
        if not reply:
            reply = "Hey! Just give me a moment. 😊"

        save_message(phone, "assistant", reply, fsm.state.value)
        send_text(phone, reply)

        # Trigger handover if qualified
        if fsm.is_qualified() and not customer.get("notified_qualified"):
            trigger_handover(
                fsm,
                notify_fn=notify_lead_qualified
            )
            log_activity(phone, "lead_qualified", fsm.collected)

    except KeyError as e:
        logger.error(f"KeyError: {e}")
    except Exception as e:
        import traceback
        logger.error(f"Webhook error: {traceback.format_exc()}")

    return "OK", 200
