from enum import Enum

class State(str, Enum):
    NEW_LEAD            = "NEW_LEAD"
    GREETING_SENT       = "GREETING_SENT"
    SERVICE_IDENTIFIED  = "SERVICE_IDENTIFIED"
    WAITING_BUSINESS_NAME = "WAITING_BUSINESS_NAME"
    BUSINESS_NAME_RECEIVED = "BUSINESS_NAME_RECEIVED"
    WAITING_NATURE      = "WAITING_NATURE"
    LEAD_QUALIFIED      = "LEAD_QUALIFIED"
    WAITING_HUMAN_REVIEW = "WAITING_HUMAN_REVIEW"
    HUMAN_ACTIVE        = "HUMAN_ACTIVE"
    NAME_CHECK_PENDING  = "NAME_CHECK_PENDING"
    NAME_AVAILABLE      = "NAME_AVAILABLE"
    NAME_UNAVAILABLE    = "NAME_UNAVAILABLE"
    WAITING_PAYMENT     = "WAITING_PAYMENT"
    REGISTRATION_IN_PROGRESS = "REGISTRATION_IN_PROGRESS"
    WAITING_BALANCE     = "WAITING_BALANCE"
    COMPLETED           = "COMPLETED"
    COLD_LEAD           = "COLD_LEAD"
    LOST                = "LOST"


VALID_TRANSITIONS = {
    State.NEW_LEAD:               [State.GREETING_SENT],
    State.GREETING_SENT:          [State.SERVICE_IDENTIFIED],
    State.SERVICE_IDENTIFIED:     [State.WAITING_BUSINESS_NAME],
    State.WAITING_BUSINESS_NAME:  [State.BUSINESS_NAME_RECEIVED],
    State.BUSINESS_NAME_RECEIVED: [State.WAITING_NATURE, State.LEAD_QUALIFIED],
    State.WAITING_NATURE:         [State.LEAD_QUALIFIED],
    State.LEAD_QUALIFIED:         [State.WAITING_HUMAN_REVIEW],
    State.WAITING_HUMAN_REVIEW:   [State.HUMAN_ACTIVE, State.NAME_CHECK_PENDING],
    State.HUMAN_ACTIVE:           [State.NAME_CHECK_PENDING, State.GREETING_SENT],
    State.NAME_CHECK_PENDING:     [State.NAME_AVAILABLE, State.NAME_UNAVAILABLE],
    State.NAME_UNAVAILABLE:       [State.WAITING_BUSINESS_NAME],
    State.NAME_AVAILABLE:         [State.WAITING_PAYMENT],
    State.WAITING_PAYMENT:        [State.REGISTRATION_IN_PROGRESS],
    State.REGISTRATION_IN_PROGRESS: [State.WAITING_BALANCE],
    State.WAITING_BALANCE:        [State.COMPLETED],
    State.COMPLETED:              [],
    State.COLD_LEAD:              [State.GREETING_SENT],
    State.LOST:                   [],
}

STATE_INSTRUCTIONS = {
    State.NEW_LEAD:
        "Greet the lead warmly and naturally. Ask what brings them here today. Do not mention any service yet. Be brief — 1 to 2 sentences.",

    State.GREETING_SENT:
        "The lead has responded. Identify what service they need. Ask naturally. Do not list all services at once.",

    State.SERVICE_IDENTIFIED:
        "You have identified the service they need. Briefly explain the service and the 3-stage payment model. Then ask for their proposed business or organization name. Be conversational — not a lecture.",

    State.WAITING_BUSINESS_NAME:
        "You are waiting for their proposed business name. If not yet provided, ask for it naturally. Mention they can provide 2 to 3 options.",

    State.BUSINESS_NAME_RECEIVED:
        "You have received their proposed business name. If the service requires it, ask naturally for the nature of the business — what products or services they will offer.",

    State.WAITING_NATURE:
        "Ask for the nature of the business if not yet provided. Keep it conversational.",

    State.LEAD_QUALIFIED:
        "You have collected everything needed. Warmly confirm receipt and let them know the team will run a CAC name availability check and be in touch shortly. Make them feel confident and taken care of.",

    State.WAITING_HUMAN_REVIEW:
        "A consultant will follow up shortly with the name availability result. Invite any final questions while they wait.",

    State.HUMAN_ACTIVE:
        "A human consultant is now handling this conversation. Do not respond unless explicitly reactivated.",

    State.NAME_AVAILABLE:
        "The name is available! Congratulate them warmly and explain the initial payment needed to reserve the name and begin registration.",

    State.NAME_UNAVAILABLE:
        "The name is not available. Empathetically explain and ask for alternative name options — 2 to 3 alternatives if possible.",

    State.WAITING_PAYMENT:
        "Provide the payment details clearly and warmly. Reassure them that registration begins immediately after payment confirmation.",

    State.REGISTRATION_IN_PROGRESS:
        "Registration is in progress. Give a warm status update and set clear timeline expectations.",

    State.WAITING_BALANCE:
        "Their certificate is ready! Congratulate them and explain the balance payment needed to receive it.",

    State.COMPLETED:
        "Registration is complete. Celebrate with them, thank them for choosing Degenius Consult LTD, and mention the referral opportunity.",
}
