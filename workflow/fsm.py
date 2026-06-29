import json
from datetime import datetime
from database.connection import DatabaseContext
from workflow.states import State, VALID_TRANSITIONS, STATE_INSTRUCTIONS, STATE_REQUIREMENTS
from utils.logger import get_logger

logger = get_logger("fsm")


class ConversationFSM:
    """
    Finite State Machine that controls the conversation workflow.
    The FSM — not Claude — decides what stage the conversation is in
    and what Claude should ask next.
    """

    def __init__(self, phone: str):
        self.phone = phone
        self.state = State.NEW_LEAD
        self.collected = {}
        self._load()

    def _load(self):
        """Load current state and collected data from database."""
        try:
            with DatabaseContext() as cursor:
                cursor.execute(
                    "SELECT fsm_state, collected_fields FROM conversations WHERE phone = %s",
                    (self.phone,)
                )
                row = cursor.fetchone()
                if row:
                    self.state = State(row[0])
                    self.collected = json.loads(row[1]) if row[1] else {}
        except Exception as e:
            logger.error(f"FSM load error for {self.phone}: {e}")

    def _save(self):
        """Persist current state to database."""
        try:
            with DatabaseContext() as cursor:
                cursor.execute("""
                    INSERT INTO conversations (phone, fsm_state, collected_fields, updated_at)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (phone)
                    DO UPDATE SET
                        fsm_state = EXCLUDED.fsm_state,
                        collected_fields = EXCLUDED.collected_fields,
                        updated_at = CURRENT_TIMESTAMP
                """, (self.phone, self.state.value, json.dumps(self.collected)))
        except Exception as e:
            logger.error(f"FSM save error for {self.phone}: {e}")

    def transition(self, new_state: State) -> bool:
        """Attempt a state transition. Returns True if successful."""
        allowed = VALID_TRANSITIONS.get(self.state, [])
        if new_state in allowed:
            logger.info(f"[{self.phone}] FSM: {self.state} → {new_state}")
            self.state = new_state
            self._save()
            self._log_activity(f"State transition to {new_state.value}")
            return True
        logger.warning(f"[{self.phone}] Invalid transition: {self.state} → {new_state}")
        return False

    def update_collected(self, field: str, value: str):
        """Store a collected field value."""
        if value and value.strip():
            self.collected[field] = value.strip()
            self._save()
            logger.info(f"[{self.phone}] Collected '{field}': {value[:50]}")

    def is_field_collected(self, field: str) -> bool:
        return bool(self.collected.get(field))

    def get_instruction(self) -> str:
        """Return the instruction Claude should follow for current state."""
        return STATE_INSTRUCTIONS.get(self.state, "Continue the conversation naturally.")

    def get_required_field(self) -> str:
        """Return the field name Claude needs to collect at current state."""
        return STATE_REQUIREMENTS.get(self.state, "")

    def advance_from_collected(self, claude_data: dict) -> bool:
        """
        Use Claude's structured response to update collected fields
        and advance the FSM state automatically.
        """
        customer_data = claude_data.get("customer_data", {})
        advanced = False

        # Update any newly collected fields
        field_map = {
            "business_name": "proposed_business_name",
            "nature": "nature_of_business",
            "phone": "phone_number",
            "email": "email_address",
            "name": "customer_name",
            "service": "service_requested",
        }

        for claude_key, db_key in field_map.items():
            value = customer_data.get(claude_key, "")
            if value and not self.is_field_collected(db_key):
                self.update_collected(db_key, value)

        # Advance state based on what's now collected
        if self.state == State.NEW_LEAD:
            self.transition(State.GREETING_SENT)
            advanced = True

        elif self.state == State.GREETING_SENT:
            if self.collected.get("service_requested"):
                self.transition(State.SERVICE_IDENTIFIED)
                advanced = True

        elif self.state == State.SERVICE_IDENTIFIED:
            self.transition(State.WAITING_BUSINESS_NAME)
            advanced = True

        elif self.state == State.WAITING_BUSINESS_NAME:
            if self.collected.get("proposed_business_name"):
                self.transition(State.BUSINESS_NAME_RECEIVED)
                self.transition(State.WAITING_NATURE)
                advanced = True

        elif self.state == State.WAITING_NATURE:
            if self.collected.get("nature_of_business"):
                self.transition(State.WAITING_PHONE)
                advanced = True

        elif self.state == State.WAITING_PHONE:
            if self.collected.get("phone_number"):
                self.transition(State.WAITING_EMAIL)
                advanced = True

        elif self.state == State.WAITING_EMAIL:
            if self.collected.get("email_address"):
                self.transition(State.LEAD_QUALIFIED)
                advanced = True

        return advanced

    def is_lead_qualified(self) -> bool:
        return self.state == State.LEAD_QUALIFIED

    def is_paused(self) -> bool:
        try:
            with DatabaseContext() as cursor:
                cursor.execute(
                    "SELECT ai_paused FROM customers WHERE phone = %s",
                    (self.phone,)
                )
                row = cursor.fetchone()
                return row[0] if row else False
        except Exception as e:
            logger.error(f"Pause check error: {e}")
            return False

    def pause(self):
        self._set_pause(True)

    def resume(self):
        self._set_pause(False)

    def _set_pause(self, paused: bool):
        try:
            with DatabaseContext() as cursor:
                cursor.execute(
                    "UPDATE customers SET ai_paused = %s WHERE phone = %s",
                    (paused, self.phone)
                )
            label = "PAUSED" if paused else "RESUMED"
            logger.info(f"[{self.phone}] Bot {label}")
        except Exception as e:
            logger.error(f"Pause set error: {e}")

    def _log_activity(self, event: str, details: dict = None):
        try:
            with DatabaseContext() as cursor:
                cursor.execute(
                    "INSERT INTO activity_log (phone, event_type, details) VALUES (%s, %s, %s)",
                    (self.phone, event, json.dumps(details or {}))
                )
        except Exception as e:
            logger.error(f"Activity log error: {e}")

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "state": self.state.value,
            "collected": self.collected,
        }
