from datetime import datetime, timedelta
from database.connection import DB
from database.models import update_conversation
from services.whatsapp import send_text
from services.notification import notify_followup_sent, send_daily_report
from config.settings import Config
from utils.logger import get_logger
import random

logger = get_logger("scheduler")

FOLLOWUP_MESSAGES = [
    "Hey! Just checking in 😊 We were chatting about registering your business — are you still interested? Happy to help.",
    "Hi! Sodiq here from Degenius. Just a gentle reminder — business names on CAC are first come first served. Shall we get yours secured? 😊",
    "Hello! Hope all is well. Whenever you're ready to get your business officially registered, just send a message and we'll continue right away. 🙏",
    "Hi! Just wanted to check if you had any questions about our registration process. We're here to make it completely stress-free for you. 😊"
]


def run_followups():
    logger.info("Running follow-up job...")
    try:
        with DB() as c:
            cutoff = datetime.utcnow() - timedelta(hours=Config.FOLLOWUP_HOURS)
            c.execute("""
                SELECT cust.phone, conv.followup_count
                FROM customers cust
                JOIN conversations conv ON cust.phone = conv.phone
                WHERE cust.last_message_at < %s
                AND cust.ai_paused = FALSE
                AND cust.within_24h_window = TRUE
                AND conv.fsm_state NOT IN ('COMPLETED','LOST','HUMAN_ACTIVE','LEAD_QUALIFIED')
                AND conv.notified_new = TRUE
                AND (conv.last_followup_at IS NULL OR conv.last_followup_at < %s)
                AND conv.followup_count < %s
            """, (cutoff, cutoff, Config.MAX_FOLLOWUPS))

            inactive = c.fetchall()
            logger.info(f"Found {len(inactive)} leads for follow-up")

        for phone, count in inactive:
            message = FOLLOWUP_MESSAGES[count % len(FOLLOWUP_MESSAGES)]
            if send_text(phone, message):
                update_conversation(
                    phone,
                    followup_count=count + 1,
                    last_followup_at=datetime.utcnow()
                )
                with DB() as c:
                    c.execute(
                        "INSERT INTO followup_log (phone, message_sent) VALUES (%s, %s)",
                        (phone, message)
                    )
                notify_followup_sent(phone, count + 1)
                logger.info(f"Follow-up #{count+1} sent to +{phone}")

    except Exception as e:
        logger.error(f"Follow-up job error: {e}")


def run_daily_report():
    logger.info("Running daily report...")
    try:
        with DB() as c:
            c.execute("""
                SELECT cust.phone, cust.full_name, cust.service_requested,
                       cust.business_name, cust.ai_paused, cust.last_message_at,
                       conv.fsm_state, conv.total_messages, conv.notified_qualified
                FROM customers cust
                LEFT JOIN conversations conv ON cust.phone = conv.phone
                WHERE conv.fsm_state NOT IN ('COMPLETED','LOST')
                ORDER BY cust.last_message_at DESC NULLS LAST
                LIMIT 50
            """)
            rows = c.fetchall()

        leads = [
            {
                "phone": r[0], "full_name": r[1], "service_requested": r[2],
                "business_name": r[3], "ai_paused": r[4], "last_message_at": r[5],
                "fsm_state": r[6], "total_messages": r[7], "notified_qualified": r[8],
            }
            for r in rows
        ]
        send_daily_report(leads)
        logger.info(f"Daily report sent — {len(leads)} leads")
    except Exception as e:
        logger.error(f"Daily report error: {e}")
