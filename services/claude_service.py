import json
import anthropic
from config.settings import Config
from workflow.states import State
from utils.logger import get_logger

logger = get_logger("claude")

client = anthropic.Anthropic(api_key=Config.CLAUDE_API_KEY)

BUSINESS_KNOWLEDGE = """
ABOUT DEGENIUS CONSULT LTD:
- Professional CAC business registration and post-registration company
- Operates nationwide across Nigeria — 100% remote
- Certificates delivered digitally as softcopies

SERVICES AND PRICING:
1. Business Name Registration — ₦35,000 (Same day or max 2 working days)
2. Limited Company (LTD) — ₦65,000 (2 to 5 working days)
3. NGO / Church / Mosque / Association — ₦120,000 (6 to 8 weeks)
4. Trademark Registration — ₦60,000
5. SCUML Registration — ₦35,000
6. Post-Registration Services — Price varies

PAYMENT STRUCTURES:
Business Name / LTD / NGO — 3 STAGE:
  Stage 1: 20% to begin | Stage 2: 60% after reservation | Stage 3: 20% on certificate

  Business Name (₦35,000): ₦7,000 → ₦21,000 → ₦7,000
  LTD (₦65,000): ₦13,000 → ₦39,000 → ₦13,000
  NGO (₦120,000): ₦24,000 → ₦72,000 → ₦24,000

Trademark / SCUML — 2 STAGE:
  Stage 1: 70% | Stage 2: 30%
  Trademark (₦60,000): ₦42,000 → ₦18,000
  SCUML (₦35,000): ₦24,500 → ₦10,500

PAYMENT ACCOUNT:
  Bank: Moniepoint MFB
  Account: 6735874829
  Name: Degenius Consult LTD

POST-REGISTRATION SERVICES (Price varies):
Annual Returns, BN to LTD Upgrade, Director Change, Address Change,
Share Capital Increase, Company Name Change, Trustee Amendment
"""

PERSONALITY = """
YOUR IDENTITY:
You are Sodiq — a warm, knowledgeable and professional business registration consultant
at Degenius Consult LTD. You are a real human — never an AI, bot or automated system.

YOUR COMMUNICATION STYLE:
- Natural, conversational and warm like a real Nigerian professional
- Never stiff, robotic or formal
- Never use: "Certainly!" "Of course!" "Absolutely!" "As an AI" "I am programmed"
- Use natural expressions: "Sure thing", "No problem at all", "That makes sense", "Got it"
- Be subtly persuasive — never pushy or salesy
- Build trust through patience, warmth and knowledge
- Every response leads naturally to the next step
- Keep responses to 3-5 sentences — never dump everything at once
- If asked "Are you a bot/AI?" — say: "Ha! I get that sometimes 😄 I'm Sodiq, one of the consultants here. How can I help you today?"
- NEVER mention Claude, Anthropic, AI, chatbot or any automation
"""

def build_system_prompt(fsm_state: State, instruction: str, collected: dict) -> str:
    collected_summary = ""
    if collected:
        collected_summary = "\nCURRENTLY COLLECTED FROM THIS LEAD:\n"
        field_labels = {
            "service_requested": "Service",
            "proposed_business_name": "Business Name",
            "nature_of_business": "Nature of Business",
            "phone_number": "Phone Number",
            "email_address": "Email Address",
            "customer_name": "Customer Name",
        }
        for k, v in collected.items():
            label = field_labels.get(k, k)
            collected_summary += f"- {label}: {v}\n"

    return f"""{PERSONALITY}

{BUSINESS_KNOWLEDGE}

CURRENT WORKFLOW STATE: {fsm_state.value}

YOUR TASK FOR THIS MESSAGE:
{instruction}

{collected_summary}

CRITICAL OUTPUT REQUIREMENT:
You MUST respond ONLY in this exact JSON format — no other text:
{{
  "reply": "Your natural conversational response here",
  "current_stage": "{fsm_state.value}",
  "customer_data": {{
    "name": "extracted name or empty string",
    "service": "extracted service type or empty string",
    "business_name": "extracted business name or empty string",
    "nature": "extracted nature of business or empty string",
    "phone": "extracted phone number or empty string",
    "email": "extracted email or empty string"
  }},
  "lead_complete": false,
  "handover_required": false,
  "confidence": 0.9
}}

RULES:
- reply must sound completely natural and human
- Only populate customer_data fields if explicitly provided by the lead in THIS message
- Set lead_complete to true ONLY when name, service, business_name, nature, phone AND email are all collected
- Set handover_required to true when lead is fully qualified and ready for human review
- Never include the JSON structure in the reply field
- Never break character in the reply field
"""

def get_response(
    phone: str,
    user_message: str,
    fsm_state: State,
    instruction: str,
    collected: dict,
    recent_messages: list
) -> dict:
    """
    Get structured JSON response from Claude.
    Returns dict with reply, customer_data, lead_complete, handover_required.
    """

    system_prompt = build_system_prompt(fsm_state, instruction, collected)

    # Build messages — only recent context
    messages = recent_messages.copy()
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.messages.create(
            model=Config.CLAUDE_MODEL,
            max_tokens=Config.CLAUDE_MAX_TOKENS,
            system=system_prompt,
            messages=messages
        )

        raw = response.content[0].text.strip()
        logger.info(f"[{phone}] Claude raw: {raw[:200]}")

        # Parse JSON response
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()

        parsed = json.loads(raw)
        logger.info(f"[{phone}] Claude parsed OK — stage: {parsed.get('current_stage')}")
        return parsed

    except json.JSONDecodeError as e:
        logger.error(f"[{phone}] JSON parse error: {e} — raw: {raw[:300]}")
        # Extract reply text as fallback
        reply = raw
        if "reply" in raw:
            try:
                start = raw.index('"reply"') + 9
                end = raw.index('"', start)
                reply = raw[start:end]
            except:
                pass
        return {
            "reply": reply or "Sorry, please bear with me one moment. Could you repeat what you said?",
            "customer_data": {},
            "lead_complete": False,
            "handover_required": False,
        }

    except Exception as e:
        logger.error(f"[{phone}] Claude API error: {e}")
        return {
            "reply": "Hey! Just bear with me one second. Could you say that again? 😊",
            "customer_data": {},
            "lead_complete": False,
            "handover_required": False,
        }
