from enum import Enum

class State(str, Enum):
    """
    Finite State Machine states for Degenius WhatsApp AI Agent.
    Each state represents a specific point in the lead conversion journey.
    """

    # Entry states
    NEW_LEAD = "NEW_LEAD"
    GREETING_SENT = "GREETING_SENT"

    # Qualification states
    SERVICE_IDENTIFIED = "SERVICE_IDENTIFIED"
    WAITING_BUSINESS_NAME = "WAITING_BUSINESS_NAME"
    BUSINESS_NAME_RECEIVED = "BUSINESS_NAME_RECEIVED"
    WAITING_NATURE = "WAITING_NATURE"
    WAITING_PHONE = "WAITING_PHONE"
    WAITING_EMAIL = "WAITING_EMAIL"

    # Lead qualified
    LEAD_QUALIFIED = "LEAD_QUALIFIED"
    WAITING_HUMAN_REVIEW = "WAITING_HUMAN_REVIEW"

    # Human handover
    HUMAN_ACTIVE = "HUMAN_ACTIVE"

    # Registration states
    NAME_CHECK_PENDING = "NAME_CHECK_PENDING"
    NAME_AVAILABLE = "NAME_AVAILABLE"
    NAME_UNAVAILABLE = "NAME_UNAVAILABLE"
    WAITING_INITIAL_PAYMENT = "WAITING_INITIAL_PAYMENT"
    INITIAL_PAYMENT_RECEIVED = "INITIAL_PAYMENT_RECEIVED"
    REGISTRATION_IN_PROGRESS = "REGISTRATION_IN_PROGRESS"
    WAITING_BALANCE_PAYMENT = "WAITING_BALANCE_PAYMENT"

    # Terminal states
    COMPLETED = "COMPLETED"
    COLD_LEAD = "COLD_LEAD"
    LOST = "LOST"


# Valid transitions — FSM enforces these
VALID_TRANSITIONS = {
    State.NEW_LEAD: [State.GREETING_SENT],
    State.GREETING_SENT: [State.SERVICE_IDENTIFIED],
    State.SERVICE_IDENTIFIED: [State.WAITING_BUSINESS_NAME],
    State.WAITING_BUSINESS_NAME: [State.BUSINESS_NAME_RECEIVED],
    State.BUSINESS_NAME_RECEIVED: [State.WAITING_NATURE],
    State.WAITING_NATURE: [State.WAITING_PHONE],
    State.WAITING_PHONE: [State.WAITING_EMAIL],
    State.WAITING_EMAIL: [State.LEAD_QUALIFIED],
    State.LEAD_QUALIFIED: [State.WAITING_HUMAN_REVIEW, State.NAME_CHECK_PENDING],
    State.WAITING_HUMAN_REVIEW: [State.HUMAN_ACTIVE, State.NAME_CHECK_PENDING],
    State.HUMAN_ACTIVE: [State.NAME_CHECK_PENDING, State.GREETING_SENT],
    State.NAME_CHECK_PENDING: [State.NAME_AVAILABLE, State.NAME_UNAVAILABLE],
    State.NAME_UNAVAILABLE: [State.WAITING_BUSINESS_NAME],
    State.NAME_AVAILABLE: [State.WAITING_INITIAL_PAYMENT],
    State.WAITING_INITIAL_PAYMENT: [State.INITIAL_PAYMENT_RECEIVED],
    State.INITIAL_PAYMENT_RECEIVED: [State.REGISTRATION_IN_PROGRESS],
    State.REGISTRATION_IN_PROGRESS: [State.WAITING_BALANCE_PAYMENT],
    State.WAITING_BALANCE_PAYMENT: [State.COMPLETED],
    State.COMPLETED: [],
    State.COLD_LEAD: [State.GREETING_SENT],
    State.LOST: [],
}

# What information Claude must collect at each state
STATE_REQUIREMENTS = {
    State.WAITING_BUSINESS_NAME: "proposed_business_name",
    State.WAITING_NATURE: "nature_of_business",
    State.WAITING_PHONE: "phone_number",
    State.WAITING_EMAIL: "email_address",
}

# Instructions Claude receives for each state
STATE_INSTRUCTIONS = {
    State.NEW_LEAD: "Greet the lead warmly and naturally. Ask what brings them here today. Do not mention any services yet.",

    State.GREETING_SENT: "The lead has responded. Identify what service they need. Ask naturally — don't list all services at once.",

    State.SERVICE_IDENTIFIED: "You have identified the service. Explain the service briefly and mention the pay-in-stages model naturally. Ask for their proposed business/organization name.",

    State.WAITING_BUSINESS_NAME: "You are waiting for their proposed business name. If they haven't provided it yet, ask for it naturally. Accept 2-3 name options.",

    State.BUSINESS_NAME_RECEIVED: "You have received their business name. Now ask naturally about the nature of their business — what products or services they'll be offering.",

    State.WAITING_NATURE: "Ask for the nature of the business if not yet provided. Be conversational.",

    State.WAITING_PHONE: "Ask for their phone number naturally. You can say you need it for updates and documentation.",

    State.WAITING_EMAIL: "Ask for their email address. Let them know it's needed for their certificate and correspondence.",

    State.LEAD_QUALIFIED: "Excellent — you have all the information needed. Warmly confirm you have everything and let them know the team will run a name availability check and be in touch shortly. Make them feel confident and excited.",

    State.WAITING_HUMAN_REVIEW: "The consultant will follow up soon with the name availability result. Reassure the lead and invite any final questions.",

    State.HUMAN_ACTIVE: "A human consultant is now handling this conversation. Do not respond unless explicitly reactivated.",

    State.NAME_AVAILABLE: "The name is available! Congratulate them and explain the initial payment needed to reserve the name.",

    State.NAME_UNAVAILABLE: "The name is not available. Empathetically explain and ask for alternative name options.",

    State.WAITING_INITIAL_PAYMENT: "Explain the initial payment clearly with account details. Reassure them registration begins immediately after confirmation.",

    State.REGISTRATION_IN_PROGRESS: "Registration is in progress. Give a warm status update and set timeline expectations.",

    State.WAITING_BALANCE_PAYMENT: "Their certificate is ready! Congratulate them and explain the balance payment needed for delivery.",

    State.COMPLETED: "Registration is complete. Celebrate with them, thank them for choosing Degenius, and mention referral opportunities.",
}
