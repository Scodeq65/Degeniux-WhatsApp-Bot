from database.models import update_conversation, log_activity
from workflow.states import State
from utils.logger import get_logger

logger = get_logger("handover")


def trigger_handover(fsm, notify_fn):
    """
    Pause the AI and notify the human consultant.
    Called automatically when lead is fully qualified.
    """
    fsm.pause()
    fsm.transition(State.WAITING_HUMAN_REVIEW)
    update_conversation(fsm.phone, notified_qualified=True)
    log_activity(fsm.phone, "handover_triggered")
    notify_fn(fsm.phone, fsm.collected)
    logger.info(f"[{fsm.phone}] Handover triggered.")


def resume_ai(fsm):
    """Resume AI handling after human is done."""
    fsm.resume()
    fsm.transition(State.GREETING_SENT)
    log_activity(fsm.phone, "ai_resumed")
    logger.info(f"[{fsm.phone}] AI resumed.")
