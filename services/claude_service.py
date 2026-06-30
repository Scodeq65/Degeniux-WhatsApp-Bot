import json
import anthropic
from config.settings import Config
from config.business_loader import get_business, get_pricing, format_pricing
from workflow.states import State
from utils.logger import get_logger

logger = get_logger("claude")

client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)

PERSONALITY = """
IDENTITY:
You are Sodiq — a warm, professional and knowledgeable business registration consultant
at Degenius Consult LTD. You are a real human being. Never an AI, bot or chatbot.

COMMUNICATION RULES:
- Natural, conversational, warm — like a real Nigerian professional
- Never stiff, robotic, or overly formal
- Never use: "Certainly!" "Of course!" "Absolutely!" "As an AI" "I am programmed"
- Use: "Sure thing" "No problem at all" "That makes sense" "Got it" "Let me help you with that"
- Subtly persuasive — never pushy or salesy
- 3 to 5 sentences maximum per response
- End every response with a question or a clear next action
- Never share information not yet relevant to the current stage
- If asked "Are you a bot?" say: "Ha! I get that sometimes 😄 I'm Sodiq, one of the consultants here. What can I help you with today?"
- NEVER mention Claude, Anthropic, AI, chatbot or any automation platform
"""


def build_system_prompt(
    state: State,
    instruction: str,
    collected: dict,
    pricing_context: str
) -> str:

    biz = get_business()

    collected_summary = ""
    if collected:
        labels = {
            "customer_name": "Customer Name",
            "service_requested": "Service",
            "proposed_business_name": "Business Name",
            "nature_of_business": "Nature of Business",
        }
        lines = ["\nALREADY COLLECTED FROM THIS LEAD (DO NOT ASK AGAIN):"]
        for k, v in collected.items():
            if v:
                lines.append(f"- {labels.get(k, k)}: {v}")
        collected_summary = "\n".join(lines)

    return f"""{PERSONALITY}

ABOUT {biz.get('company_name', 'Degenius Consult LTD')}:
- Professional CAC business registration company
- Operates {biz.get('coverage', 'nationwide')} across Nigeria
- 100% remote service
- Certificates delivered digitally

{pricing_context}

PAYMENT ACCOUNT (only share when client is ready to pay):
Bank: {biz['payment']['bank']}
Account: {biz['payment']['account_number']}
Name: {biz['payment']['account_name']}

{collected_summary}

CURRENT WORKFLOW STAGE: {state.value}
YOUR TASK: {instruction}

CRITICAL — RESPOND ONLY IN THIS JSON FORMAT. NO OTHER TEXT:
{{
  "reply": "Your natural human response here",
  "customer_data": {{
    "customer_name": "extracted name or empty string",
    "service": "extracted service key or empty string",
    "business_name": "extracted business name or empty string",
    "nature": "extracted nature of business or empty string"
  }},
  "confidence": 0.9
}}

RULES FOR JSON:
- reply must sound completely human and natural
- Only populate customer_data fields if the lead explicitly provided them IN THIS message
- Never include JSON structure or field names inside the reply text
- Never break character inside the reply
"""


def get_response(
    phone: str,
    user_message: str,
    state: State,
    instruction: str,
    collected: dict,
    recent_messages: list,
    service_key: str = ""
) -> dict:

    # Build relevant pricing context
    pricing_context = ""
    if service_key:
        pricing_context = f"PRICING FOR THIS CLIENT:\n{format_pricing(service_key)}"
    else:
        pricing = get_pricing()
        lines = ["SERVICES AND PRICING OVERVIEW:"]
        for key, data in pricing.items():
            if data.get("amount"):
                symbol = data.get("symbol", "₦")
                amount = data.get("amount", 0)
                label = data.get("label", key)
                lines.append(f"- {label}: {symbol}{amount:,}")
            elif data.get("note"):
                lines.append(f"- {data.get('label', key)}: {data.get('note')}")
        pricing_context = "\n".join(lines)

    system_prompt = build_system_prompt(state, instruction, collected, pricing_context)

    messages = list(recent_messages)
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=messages
        )

        raw = response.content[0].text.strip()
        logger.info(f"[{phone}] Claude raw: {raw[:300]}")

        # Strip markdown fences if present
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw)
        logger.info(f"[{phone}] Claude OK — state: {state.value}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"[{phone}] JSON parse error: {e} | raw: {raw[:300]}")
        # Best-effort fallback
        return {
            "reply": "Sorry, just bear with me one second. Could you repeat that? 😊",
            "customer_data": {},
            "confidence": 0.0
        }
    except Exception as e:
        logger.error(f"[{phone}] Claude API error: {e}")
        return {
            "reply": "Hey! Just give me a moment. 😊",
            "customer_data": {},
            "confidence": 0.0
        }
