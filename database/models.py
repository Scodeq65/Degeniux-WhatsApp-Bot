import json
from datetime import datetime
from database.connection import DB
from utils.logger import get_logger

logger = get_logger("models")


def ensure_customer(phone: str):
    try:
        with DB() as c:
            c.execute(
                "INSERT INTO customers (phone) VALUES (%s) ON CONFLICT (phone) DO NOTHING",
                (phone,)
            )
            c.execute(
                "INSERT INTO conversations (phone) VALUES (%s) ON CONFLICT (phone) DO NOTHING",
                (phone,)
            )
    except Exception as e:
        logger.error(f"ensure_customer error: {e}")


def get_customer(phone: str) -> dict:
    try:
        with DB() as c:
            c.execute("""
                SELECT c.phone, c.full_name, c.service_requested, c.business_name,
                       c.nature_of_business, c.ai_paused, c.last_message_at,
                       cv.fsm_state, cv.collected_fields, cv.total_messages,
                       cv.notified_new, cv.notified_qualified, cv.followup_count
                FROM customers c
                JOIN conversations cv ON c.phone = cv.phone
                WHERE c.phone = %s
            """, (phone,))
            row = c.fetchone()
            if not row:
                return {}
            return {
                "phone": row[0],
                "full_name": row[1],
                "service_requested": row[2],
                "business_name": row[3],
                "nature_of_business": row[4],
                "ai_paused": row[5],
                "last_message_at": row[6],
                "fsm_state": row[7],
                "collected_fields": row[8] or {},
                "total_messages": row[9],
                "notified_new": row[10],
                "notified_qualified": row[11],
                "followup_count": row[12],
            }
    except Exception as e:
        logger.error(f"get_customer error: {e}")
        return {}


def update_customer(phone: str, **kwargs):
    if not kwargs:
        return
    try:
        with DB() as c:
            fields = ", ".join(f"{k} = %s" for k in kwargs)
            values = list(kwargs.values()) + [phone]
            c.execute(
                f"UPDATE customers SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE phone = %s",
                values
            )
    except Exception as e:
        logger.error(f"update_customer error: {e}")


def update_conversation(phone: str, **kwargs):
    if not kwargs:
        return
    try:
        with DB() as c:
            fields = ", ".join(f"{k} = %s" for k in kwargs)
            values = list(kwargs.values()) + [phone]
            c.execute(
                f"UPDATE conversations SET {fields}, updated_at = CURRENT_TIMESTAMP WHERE phone = %s",
                values
            )
    except Exception as e:
        logger.error(f"update_conversation error: {e}")


def update_collected_fields(phone: str, new_fields: dict):
    try:
        with DB() as c:
            c.execute(
                "SELECT collected_fields FROM conversations WHERE phone = %s",
                (phone,)
            )
            row = c.fetchone()
            existing = dict(row[0]) if row and row[0] else {}
            existing.update({k: v for k, v in new_fields.items() if v})
            c.execute(
                "UPDATE conversations SET collected_fields = %s, updated_at = CURRENT_TIMESTAMP WHERE phone = %s",
                (json.dumps(existing), phone)
            )
    except Exception as e:
        logger.error(f"update_collected_fields error: {e}")


def save_message(phone: str, role: str, content: str, state: str):
    try:
        with DB() as c:
            c.execute(
                "INSERT INTO messages (phone, role, content, fsm_state) VALUES (%s, %s, %s, %s)",
                (phone, role, content, state)
            )
            c.execute(
                "UPDATE conversations SET total_messages = total_messages + 1, updated_at = CURRENT_TIMESTAMP WHERE phone = %s",
                (phone,)
            )
    except Exception as e:
        logger.error(f"save_message error: {e}")


def get_recent_messages(phone: str, limit: int = 8) -> list:
    try:
        with DB() as c:
            c.execute("""
                SELECT role, content FROM messages
                WHERE phone = %s ORDER BY created_at DESC LIMIT %s
            """, (phone, limit))
            rows = c.fetchall()
            return [{"role": r[0], "content": r[1]} for r in reversed(rows)]
    except Exception as e:
        logger.error(f"get_recent_messages error: {e}")
        return []


def get_all_active_leads() -> list:
    try:
        with DB() as c:
            c.execute("""
                SELECT c.phone, c.full_name, c.service_requested, c.business_name,
                       c.ai_paused, c.last_message_at,
                       cv.fsm_state, cv.total_messages, cv.notified_qualified,
                       cv.followup_count
                FROM customers c
                LEFT JOIN conversations cv ON c.phone = cv.phone
                WHERE cv.fsm_state NOT IN ('COMPLETED','LOST')
                ORDER BY c.last_message_at DESC NULLS LAST
                LIMIT 100
            """)
            rows = c.fetchall()
            return [
                {
                    "phone": r[0],
                    "full_name": r[1],
                    "service_requested": r[2],
                    "business_name": r[3],
                    "ai_paused": r[4],
                    "last_message_at": r[5],
                    "fsm_state": r[6],
                    "total_messages": r[7],
                    "notified_qualified": r[8],
                    "followup_count": r[9],
                }
                for r in rows
            ]
    except Exception as e:
        logger.error(f"get_all_active_leads error: {e}")
        return []


def log_activity(phone: str, event: str, details: dict = None):
    try:
        with DB() as c:
            c.execute(
                "INSERT INTO activity_log (phone, event_type, details) VALUES (%s, %s, %s)",
                (phone, event, json.dumps(details or {}))
            )
    except Exception as e:
        logger.error(f"log_activity error: {e}")
