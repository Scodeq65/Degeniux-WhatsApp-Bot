import json
from database.connection import DB
from database.models import update_conversation, update_customer, update_collected_fields, log_activity
from workflow.states import State, VALID_TRANSITIONS, STATE_INSTRUCTIONS
from config.business_loader import identify_service, get_services
from utils.logger import get_logger

logger = get_logger("fsm")


class FSM:
    """
    Finite State Machine controlling the entire conversation workflow.
    The FSM owns the business logic. Claude only generates language.
    """

    def __init__(self, phone: str, customer: dict):
        self.phone = phone
        self.state = State(customer.get("fsm_state", State.NEW_LEAD))
        self.collected = dict(customer.get("collected_fields") or {})
        self.customer = customer

    def transition(self, new_state: State) -> bool:
        allowed = VALID_TRANSITIONS.get(self.state, [])
        if new_state in allowed:
            logger.info(f"[{self.phone}] {self.state} → {new_state}")
            self.state = new_state
            update_conversation(self.phone, fsm_state=self.state.value)
            log_activity(self.phone, f"transition_{new_state.value}")
            return True
        logger.warning(f"[{self.phone}] Blocked transition: {self.state} → {new_state}")
        return False

    def store(self, field: str, value: str):
        if value and str(value).strip():
            self.collected[field] = str(value).strip()
            update_collected_fields(self.phone, {field: str(value).strip()})
            logger.info(f"[{self.phone}] Stored '{field}'")

    def has(self, field: str) -> bool:
        return bool(self.collected.get(field))

    def get_instruction(self) -> str:
        return STATE_INSTRUCTIONS.get(self.state, "Continue the conversation naturally.")

    def is_paused(self) -> bool:
        return bool(self.customer.get("ai_paused"))

    def pause(self):
        update_customer(self.phone, ai_paused=True)
        log_activity(self.phone, "bot_paused")
        logger.info(f"[{self.phone}] Bot PAUSED")

    def resume(self):
        update_customer(self.phone, ai_paused=False)
        log_activity(self.phone, "bot_resumed")
        logger.info(f"[{self.phone}] Bot RESUMED")

    def process_extracted(self, extracted: dict) -> bool:
        """
        Apply extracted data from Claude and advance FSM automatically.
        Returns True if state advanced.
        """
        advanced = False

        # Store any newly extracted values
        field_map = {
            "customer_name": "customer_name",
            "service": "service_requested",
            "business_name": "proposed_business_name",
            "nature": "nature_of_business",
        }
        for claude_key, store_key in field_map.items():
            value = extracted.get(claude_key, "")
            if value and not self.has(store_key):
                self.store(store_key, value)
                # Sync to customer profile
                if store_key == "customer_name":
                    update_customer(self.phone, full_name=value)
                elif store_key == "service_requested":
                    update_customer(self.phone, service_requested=value)
                elif store_key == "proposed_business_name":
                    update_customer(self.phone, business_name=value)
                elif store_key == "nature_of_business":
                    update_customer(self.phone, nature_of_business=value)

        # Identify service from message if not yet stored
        if not self.has("service_requested"):
            raw_text = extracted.get("raw_message", "")
            if raw_text:
                detected = identify_service(raw_text)
                if detected:
                    self.store("service_requested", detected)
                    update_customer(self.phone, service_requested=detected)

        # FSM advancement logic
        if self.state == State.NEW_LEAD:
            self.transition(State.GREETING_SENT)
            advanced = True

        elif self.state == State.GREETING_SENT:
            if self.has("service_requested"):
                self.transition(State.SERVICE_IDENTIFIED)
                advanced = True

        elif self.state == State.SERVICE_IDENTIFIED:
            self.transition(State.WAITING_BUSINESS_NAME)
            advanced = True

        elif self.state == State.WAITING_BUSINESS_NAME:
            if self.has("proposed_business_name"):
                self.transition(State.BUSINESS_NAME_RECEIVED)
                advanced = True

        elif self.state == State.BUSINESS_NAME_RECEIVED:
            service_key = self.collected.get("service_requested", "")
            services = get_services()
            needs_nature = any(
                s["key"] == service_key and s.get("requires_nature")
                for s in services.get("registration", [])
            )
            if needs_nature and not self.has("nature_of_business"):
                self.transition(State.WAITING_NATURE)
            else:
                self.transition(State.LEAD_QUALIFIED)
            advanced = True

        elif self.state == State.WAITING_NATURE:
            if self.has("nature_of_business"):
                self.transition(State.LEAD_QUALIFIED)
                advanced = True

        return advanced

    def is_qualified(self) -> bool:
        return self.state == State.LEAD_QUALIFIED

    def to_dict(self) -> dict:
        return {
            "phone": self.phone,
            "state": self.state.value,
            "collected": self.collected,
        }
