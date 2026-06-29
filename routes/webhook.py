import json
from flask import Blueprint, request
from workflow.fsm import ConversationFSM
from workflow.states import State
from services.whatsapp import WhatsAppService
from services.claude_service import get_response
from services.notification import notify_new_lead, notify_lead_qualified
from database.connection import DatabaseContext
from config.settings import Config
from utils.logger import get_logger

webhook_bp = Blueprint("webhook", __name__)
logger = get_logger("webhook")


def ensure_customer_exists(phone: str):
    """Create customer record if not exists."""
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "INSERT INTO customers (phone) VALUES (%s) ON CONFLICT (phone) DO NOTHING",
                (phone,)
            )
    except Exception as e:
        logger.error(f"Customer create error: {e}")


def update_customer_from_collected(phone: str, collected: dict):
    """Sync collected fields to customer profile."""
    try:
        with DatabaseContext() as cursor:
            cursor.execute("""
                UPDATE customers SET
                    full_name = COALESCE(NULLIF(%s,''), full_name),
                    email = COALESCE(NULLIF(%s,''), email),
                    service_requested = COALESCE(NULLIF(%s,''), service_requested),
                    business_name = COALESCE(NULLIF(%s,''), business_name),
                    nature_of_business = COALESCE(NULLIF(%s,''), nature_of_business),
                    lead_stage = %s,
                    last_customer_message_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE phone = %s
            """, (
                collected.get('customer_name', ''),
                collected.get('email_address', ''),
                collected.get('service_requested', ''),
                collected.get('proposed_business_name', ''),
                collected.get('nature_of_business', ''),
                collected.get('fsm_state', 'new_lead'),
                phone
            ))
    except Exception as e:
        logger.error(f"Customer update error: {e}")


def save_message(phone: str, role: str, content: str, state: str):
    """Save individual message to messages table."""
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "INSERT INTO messages (phone, role, content, fsm_state) VALUES (%s, %s, %s, %s)",
                (phone, role, content, state)
            )
            cursor.execute(
                "UPDATE conversations SET total_messages = total_messages + 1 WHERE phone = %s",
                (phone,)
            )
    except Exception as e:
        logger.error(f"Message save error: {e}")


def get_recent_messages(phone: str, limit: int = 10) -> list:
    """Retrieve recent messages for Claude context."""
    try:
        with DatabaseContext() as cursor:
            cursor.execute("""
                SELECT role, content FROM messages
                WHERE phone = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (phone, limit))
            rows = cursor.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        logger.error(f"Get messages error: {e}")
        return []


def has_been_notified_new(phone: str) -> bool:
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "SELECT notified_new FROM conversations WHERE phone = %s",
                (phone,)
            )
            row = cursor.fetchone()
            return row[0] if row else False
    except:
        return False


def mark_notified_new(phone: str):
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "UPDATE conversations SET notified_new = TRUE WHERE phone = %s",
                (phone,)
            )
    except Exception as e:
        logger.error(f"Mark notified error: {e}")


def mark_notified_qualified(phone: str):
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "UPDATE conversations SET notified_qualified = TRUE WHERE phone = %s",
                (phone,)
            )
    except Exception as e:
        logger.error(f"Mark qualified error: {e}")


def has_been_notified_qualified(phone: str) -> bool:
    try:
        with DatabaseContext() as cursor:
            cursor.execute(
                "SELECT notified_qualified FROM conversations WHERE phone = %s",
                (phone,)
            )
            row = cursor.fetchone()
            return row[0] if row else False
    except:
        return False


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
    logger.info(f"Webhook received: {json.dumps(data)[:500]}")

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        # Ignore delivery/read status updates
        if "statuses" in value and "messages" not in value:
            return "OK", 200

        if "messages" not in value:
            return "OK", 200

        message = value["messages"][0]
        phone = message["from"]
        message_type = message.get("type", "")
        message_id = message.get("id", "")

        logger.info(f"Message from +{phone} — type: {message_type}")

        # Mark as read
        if message_id:
            WhatsAppService.mark_read(message_id)

        # Handle non-text messages
        if message_type != "text":
            WhatsAppService.handle_media_message(phone, message_type)
            return "OK", 200

        user_message = message["text"]["body"].strip()
        if not user_message:
            return "OK", 200

        # Ensure customer exists
        ensure_customer_exists(phone)

        # Load FSM
        fsm = ConversationFSM(phone)

        # Check if bot is paused
        if fsm.is_paused():
            logger.info(f"Bot paused for +{phone} — skipping AI")
            return "OK", 200

        # Notify on first message
        if not has_been_notified_new(phone):
            notify_new_lead(phone)
            mark_notified_new(phone)

        # Save user message
        save_message(phone, "user", user_message, fsm.state.value)

        # Get recent messages for context
        recent = get_recent_messages(phone, limit=8)

        # Get instruction from FSM
        instruction = fsm.get_instruction()

        # Get Claude structured response
        claude_data = get_response(
            phone=phone,
            user_message=user_message,
            fsm_state=fsm.state,
            instruction=instruction,
            collected=fsm.collected,
            recent_messages=recent[:-1]  # Exclude the message we just added
        )

        # Extract reply
        reply = claude_data.get("reply", "").strip()
        if not reply:
            reply = "Hey! Just give me one second. 😊"

        # Update FSM from Claude's extracted data
        fsm.advance_from_collected(claude_data)

        # Update customer profile
        update_customer_from_collected(phone, {**fsm.collected, "fsm_state": fsm.state.value})

        # Save AI message
        save_message(phone, "assistant", reply, fsm.state.value)

        # Send reply to WhatsApp
        WhatsAppService.send_text(phone, reply)

        # Handle lead qualified
        if (fsm.is_lead_qualified() and not has_been_notified_qualified(phone)):
            notify_lead_qualified(phone, fsm.collected)
            mark_notified_qualified(phone)
            # Auto-pause bot — human should review
            fsm.pause()
            logger.info(f"Bot auto-paused for qualified lead +{phone}")

        # Handle explicit handover request
        elif claude_data.get("handover_required") and not has_been_notified_qualified(phone):
            notify_lead_qualified(phone, fsm.collected)
            mark_notified_qualified(phone)
            fsm.pause()

    except KeyError as e:
        logger.error(f"KeyError processing webhook: {e}")
    except Exception as e:
        import traceback
        logger.error(f"Webhook error: {traceback.format_exc()}")

    return "OK", 200
