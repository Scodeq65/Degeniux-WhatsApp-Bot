from datetime import datetime, timedelta
from database.connection import DatabaseContext
from services.whatsapp import WhatsAppService
from services.notification import notify_followup_sent, send_daily_report
from config.settings import Config
from utils.logger import get_logger
import random

logger = get_logger("scheduler")

FOLLOWUP_MESSAGES = [
    "Hey! Just checking in 😊 We were chatting about getting your business registered — are you still interested? Happy to answer any questions.",
    "Hi! Sodiq here from Degenius Consult LTD. Just a gentle reminder — business names on CAC are first come first served. Shall we get yours secured? 😊",
    "Hello! Hope all is well. Whenever you're ready to get your business officially registered, just send a message and we'll pick up right where we left off. 🙏",
    "Hi! Just wanted to check if you had any questions about the registration process. We're here to make it completely stress-free for you. 😊"
]


def run_followups():
    """Send follow-up messages to inactive leads within 24h window."""
    logger.info("Running follow-up job...")
    conn = None
    try:
        with DatabaseContext() as cursor:
            cutoff = datetime.utcnow() - timedelta(hours=Config.FOLLOWUP_HOURS)

            cursor.execute("""
                SELECT c.phone, cv.followup_count
                FROM customers c
                JOIN conversations cv ON c.phone = cv.phone
                WHERE c.last_customer_message_at < %s
                AND c.ai_paused = FALSE
                AND c.within_24h_window = TRUE
                AND cv.fsm_state NOT IN ('COMPLETED', 'COLD_LEAD', 'LOST', 'HUMAN_ACTIVE')
                AND cv.notified_new = TRUE
                AND (cv.last_followup_at IS NULL OR cv.last_followup_at < %s)
                AND cv.followup_count < 3
            """, (cutoff, cutoff))

            inactive = cursor.fetchall()
            logger.info(f"Found {len(inactive)} inactive leads for follow-up")

            for phone, followup_count in inactive:
                message = FOLLOWUP_MESSAGES[followup_count % len(FOLLOWUP_MESSAGES)]

                sent = WhatsAppService.send_text(phone, message)
                if sent:
                    cursor.execute("""
                        UPDATE conversations SET
                            followup_count = followup_count + 1,
                            last_followup_at = CURRENT_TIMESTAMP
                        WHERE phone = %s
                    """, (phone,))

                    cursor.execute("""
                        INSERT INTO followup_log (phone, message_sent)
                        VALUES (%s, %s)
                    """, (phone, message))

                    notify_followup_sent(phone)
                    logger.info(f"Follow-up #{followup_count+1} sent to +{phone}")

    except Exception as e:
        logger.error(f"Follow-up job error: {e}")


def run_daily_report():
    """Send daily summary report via Telegram."""
    logger.info("Running daily report job...")
    try:
        with DatabaseContext() as cursor:
            cursor.execute("""
                SELECT c.phone, c.full_name, c.service_requested, c.business_name,
                       c.ai_paused, c.last_customer_message_at,
                       cv.fsm_state, cv.total_messages
                FROM customers c
                LEFT JOIN conversations cv ON c.phone = cv.phone
                WHERE cv.fsm_state NOT IN ('COMPLETED', 'LOST')
                ORDER BY c.last_customer_message_at DESC NULLS LAST
                LIMIT 50
            """)
            rows = cursor.fetchall()

            leads = []
            for row in rows:
                leads.append({
                    "phone": row[0],
                    "name": row[1],
                    "service_requested": row[2],
                    "proposed_business_name": row[3],
                    "ai_paused": row[4],
                    "last_customer_message_at": row[5],
                    "fsm_state": row[6],
                    "total_messages": row[7],
                })

        send_daily_report(leads)
        logger.info(f"Daily report sent — {len(leads)} leads")

    except Exception as e:
        logger.error(f"Daily report error: {e}")
