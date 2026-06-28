import os
import json
import requests as req
from datetime import datetime, timedelta
import anthropic

try:
    import psycopg2
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False

# ============================================================
# CONFIGURATION
# ============================================================

client = anthropic.Anthropic(api_key=os.environ.get("CLAUDE_API_KEY"))
DATABASE_URL = os.environ.get("DATABASE_URL")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
RENDER_URL = os.environ.get("RENDER_URL", "https://degeniux-whatsapp-bot.onrender.com")
CONTROL_SECRET = os.environ.get("CONTROL_SECRET", "degenius_control_2024")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")

# ============================================================
# DATABASE SETUP
# ============================================================

def get_db_connection():
    if DATABASE_URL and POSTGRES_AVAILABLE:
        return psycopg2.connect(DATABASE_URL)
    raise Exception("DATABASE_URL not set or psycopg2 not installed.")

def init_db():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS whatsapp_chats (
                user_id VARCHAR(50) PRIMARY KEY,
                history TEXT NOT NULL DEFAULT '[]',
                paused BOOLEAN DEFAULT FALSE,
                status VARCHAR(50) DEFAULT 'new',
                lead_info TEXT DEFAULT '{}',
                last_message_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                notified_start BOOLEAN DEFAULT FALSE,
                report_sent_at TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cursor.close()
        conn.close()
        print("Database initialized successfully.")
    except Exception as e:
        print(f"Database initialization error: {e}")

init_db()

# ============================================================
# SYSTEM PROMPT
# ============================================================

SYSTEM_PROMPT = """You are Sodiq, a professional and warm business registration consultant at Degenius Consult LTD in Nigeria. You speak naturally like a real Nigerian professional. You are a real person — NOT a bot, NOT an AI, NOT automated.

ABOUT DEGENIUS CONSULT LTD:
- Professional CAC business registration and post-registration company
- Operates nationwide across Nigeria
- 100% remote service — no physical appearance needed
- Certificates delivered digitally as softcopies

SERVICES AND PRICING:

1. Business Name Registration — ₦35,000 (Same day or max 2 working days)
2. Limited Company (LTD) Registration — ₦65,000 (2 to 5 working days)
3. NGO / Church / Mosque / Association Registration — ₦120,000 (6 to 8 weeks)
4. Trademark Registration — ₦60,000
5. SCUML Registration — ₦35,000
6. Post-Registration Services — Price varies (Annual Returns, Upgrades, Amendments, etc.)

PAYMENT STRUCTURES:

BUSINESS NAME, LTD, NGO — 3 STAGE PAYMENT:
Stage 1: 20% initial payment to begin
Stage 2: 60% after name reservation confirmed
Stage 3: 20% balance when certificate is ready

PAYMENT BREAKDOWN:
- Business Name (₦35,000): ₦7,000 → ₦21,000 → ₦7,000
- LTD (₦65,000): ₦13,000 → ₦39,000 → ₦13,000
- NGO/Church (₦120,000): ₦24,000 → ₦72,000 → ₦24,000

TRADEMARK & SCUML — 2 STAGE PAYMENT:
- Trademark (₦60,000): ₦42,000 (70%) → ₦18,000 (30%)
- SCUML (₦35,000): ₦24,500 (70%) → ₦10,500 (30%)

POST-REGISTRATION: Price varies — say "Let me get the exact figure for you. What specifically do you need done?"

PAYMENT ACCOUNT:
Bank: Moniepoint MFB
Account Number: 6735874829
Account Name: Degenius Consult LTD

REGISTRATION REQUIREMENTS:
IMPORTANT — Only send requirements AFTER:
1. Client's proposed name confirmed available by CAC
2. Client agrees to proceed and initial payment is made

BUSINESS NAME REQUIREMENTS (Send exactly as written below when triggered):
"Kindly provide the following for your Business Name registration:

Business Information:
- Business Address
- Phone Number
- Email Address
- Valid ID (NIN Slip, Voter's Card, National ID, Driver's License or International Passport)
- Passport photograph

Proprietor's Details:
- Full Name
- Date of Birth
- Phone Number
- Email Address
- Residential Address
- Occupation
- Signature on a plain paper"

LTD REQUIREMENTS (Send exactly when triggered):
"Kindly provide the following for your Company Registration:

1. Proposed Company Name(s) — minimum 2-3 options
2. Nature of Business
3. Registered Company Address

Directors' Details (for each director):
- Full Name, Date of Birth, Gender, Nationality
- Occupation, Phone Number, Email Address
- Residential Address, NIN

Means of ID (any one per director):
National ID, NIN Slip, Voter's Card, Driver's License or International Passport

Additional:
- Clear signature on plain paper
- Witness Details: Full Name, Phone, Occupation, Address, Signature and NIN
- Active company email and phone number"

NGO/CHURCH REQUIREMENTS (Send exactly when triggered):
"Kindly provide the following for your NGO registration:

1. Proposed Name (2 options in order of preference)

2. Organization Information:
- Aims and Objectives
- Nature of Activities
- Registered Office Address
- Areas of Operation

3. Trustees' Information (minimum 2 trustees):
For each trustee:
- Surname, First Name, Other Name
- Date of Birth, Gender, Nationality
- Occupation, Phone, Email, Residential Address

4. Executive Members:
- Chairman, Secretary, Treasurer, Others

5. Means of ID + ID Number + Expiry Date

6. Supporting Documents:
- Valid ID for all trustees
- Passport photographs for all trustees
- Signatures on plain white paper
- Constitution of the Organization
- Minutes of Meeting showing appointment of trustees
- Attendance list of the meeting
- Organization logo (optional)"

YOUR PERSONALITY:
- Warm, patient, natural and professional
- Sound like a real Nigerian professional — never stiff or formal
- Never use AI phrases: "Certainly!" "Of course!" "Absolutely!" "As an AI" "I'm here to assist"
- Use natural expressions: "Sure thing", "No problem at all", "That makes sense", "Let me help you sort that out"
- Be subtly persuasive — never pushy or salesy
- Build trust through warmth, knowledge and patience
- Guide every conversation toward a clear next step (CTA)
- Handle objections with empathy first, solution second

CONVERSATION APPROACH:
1. Greet warmly — understand exactly what they need
2. Naturally identify the service
3. Explain payment structure conversationally (make it sound easy)
4. Collect: proposed name, nature of business, phone number, email
5. Tell them team will run availability check
6. After name confirmed — collect initial payment
7. After payment received — send registration requirements
8. Keep updating them through the process warmly

OBJECTION HANDLING (natural, never scripted-sounding):
- "Too expensive" → "I totally get that. The good thing is you don't pay everything upfront — for Business Name you start with just ₦7,000 and only pay the rest as we progress. Pretty manageable right?"
- "Let me think about it" → "Sure, no rush at all. Just so you know though, business names on CAC are first come first served — someone could grab your preferred name before you come back to it. But I'm here whenever you're ready."
- "Is this legit?" → "100% legitimate. We're CAC-compliant and have processed hundreds of registrations nationwide. Your certificate comes directly from CAC — fully official."
- "I don't have money now" → "That's exactly why we structured payment the way we did. You only need ₦7,000 to get things started for Business Name. Once your name is secured you have time before the next payment. Does that work?"
- "Can you reduce?" → "I wish I could do more, but honestly our pricing is already very fair for the quality and speed we deliver. We handle absolutely everything — you just provide the details and we take it from there."

URGENCY (mention naturally, never forcefully):
- Business names are registered first come first served on CAC portal
- Someone else could register their name at any time
- Official registration gives legal protection to their brand and business

CRITICAL RULES:
- NEVER say you are an AI, bot, chatbot or automated system — ever
- NEVER mention Claude, Anthropic or any AI company
- NEVER use phrases like "As an AI", "I am programmed", "I cannot"
- ALWAYS be Sodiq — a real, warm, knowledgeable human consultant
- Keep responses to 3-5 sentences — conversational, never lectures
- Always end with a question or clear next action
- Never dump all information at once — reveal naturally in conversation
- When asked "Are you a bot/AI/human?" reply: "Ha! I get that sometimes 😄 I'm Sodiq, one of the consultants here. What can I help you with today?"

LEAD COLLECTION TAG:
When you have collected name, service, proposed business name, nature of business, phone AND email — add this at the very end of your response (after your closing line):
[LEAD_READY:name=FULL_NAME|service=SERVICE_TYPE|business_name=BUSINESS_NAME|nature=NATURE_OF_BUSINESS|phone=PHONE|email=EMAIL]
"""

# ============================================================
# TELEGRAM NOTIFICATIONS
# ============================================================

def send_telegram_message(text):
    """Send message to Telegram."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram not configured")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": False
        }
        response = req.post(url, json=payload, timeout=10)
        print(f"Telegram: {response.status_code}")
    except Exception as e:
        print(f"Telegram error: {e}")

def notify_new_lead(user_id):
    """Notify Sodiq when a new lead starts a conversation."""
    conv_url = f"{RENDER_URL}/conversation/{user_id}?secret={CONTROL_SECRET}"
    admin_url = f"{RENDER_URL}/admin?secret={CONTROL_SECRET}"

    message = f"""🔔 <b>NEW LEAD — DEGENIUS CONSULT LTD</b>

📱 <b>WhatsApp:</b> +{user_id}
⏰ <b>Time:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
🤖 <b>Status:</b> AI handling conversation

<a href="{conv_url}">📋 View Conversation</a> | <a href="{admin_url}">⚙️ Admin Panel</a>

<i>To pause AI for this lead, visit Admin Panel</i>"""

    send_telegram_message(message)

def notify_lead_ready(user_id, lead_data):
    """Notify Sodiq when lead has provided all details."""
    conv_url = f"{RENDER_URL}/conversation/{user_id}?secret={CONTROL_SECRET}"

    message = f"""🔥 <b>LEAD READY — ACTION REQUIRED!</b>

📱 <b>WhatsApp:</b> +{user_id}
👤 <b>Name:</b> {lead_data.get('name', 'Not provided')}
📧 <b>Email:</b> {lead_data.get('email', 'Not provided')}
📞 <b>Phone:</b> {lead_data.get('phone', user_id)}
🏢 <b>Service:</b> {lead_data.get('service', 'Not provided')}
📝 <b>Business Name:</b> {lead_data.get('business_name', 'Not provided')}
🏭 <b>Nature:</b> {lead_data.get('nature', 'Not provided')}

⚡ <b>YOUR NEXT STEPS:</b>
1️⃣ Run CAC name availability check
2️⃣ Inform lead of result
3️⃣ Collect initial payment
4️⃣ Begin registration

<a href="{conv_url}">📋 View Full Conversation</a>

<i>Bot is still active. Pause it in Admin Panel before taking over manually.</i>"""

    send_telegram_message(message)

# ============================================================
# FOLLOW-UP SYSTEM
# ============================================================

def send_whatsapp_direct(to, message):
    """Send WhatsApp message directly (used for follow-ups)."""
    url = f"https://graph.facebook.com/v25.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": message}
    }
    try:
        response = req.post(url, headers=headers, json=data, timeout=10)
        print(f"Follow-up to {to}: {response.status_code}")
        return response
    except Exception as e:
        print(f"Follow-up error: {e}")
        return None

def check_and_send_followups():
    """Check for inactive leads and send follow-up messages."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(hours=24)

        cursor.execute("""
            SELECT user_id FROM whatsapp_chats
            WHERE last_message_at < %s
            AND paused = FALSE
            AND status NOT IN ('completed', 'followup_sent')
            AND notified_start = TRUE
        """, (cutoff,))

        inactive = cursor.fetchall()
        cursor.close()

        for (user_id,) in inactive:
            followup_messages = [
                "Hey! Just checking in 😊 We were chatting about getting your business registered. Still interested? I'm here if you have any questions.",
                "Hi! Sodiq here from Degenius Consult LTD. Just a quick reminder — your business name could be taken on CAC at any time. Shall we get it secured? 😊",
                "Hello! Hope all is well. Registering your business officially protects your brand. Whenever you're ready, just send a message and we'll pick up right where we left off. 🙏"
            ]

            import random
            message = random.choice(followup_messages)
            send_whatsapp_direct(user_id, message)
            update_lead_status(user_id, 'followup_sent')

            # Notify on Telegram
            send_telegram_message(
                f"📤 <b>Follow-up sent to:</b> +{user_id}\n<i>Lead was inactive for 24+ hours</i>"
            )

    except Exception as e:
        print(f"Follow-up check error: {e}")
    finally:
        if conn:
            conn.close()

# ============================================================
# 3-DAY REPORT
# ============================================================

def send_3day_reports():
    """Send daily summary report of all active conversations."""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, status, paused, lead_info, last_message_at, history
            FROM whatsapp_chats
            WHERE status NOT IN ('completed')
            AND notified_start = TRUE
            ORDER BY last_message_at DESC
        """)

        leads = cursor.fetchall()
        cursor.close()

        if not leads:
            send_telegram_message("📊 <b>Daily Report:</b> No active conversations today.")
            return

        report = f"""📊 <b>DAILY LEAD REPORT — DEGENIUS CONSULT LTD</b>
📅 <b>Date:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
👥 <b>Total Active Leads:</b> {len(leads)}

"""
        for lead in leads:
            user_id, status, paused, lead_info_str, last_msg, history_str = lead

            try:
                lead_info = json.loads(lead_info_str) if lead_info_str else {}
            except:
                lead_info = {}

            try:
                history = json.loads(history_str) if history_str else []
                user_msgs = len([h for h in history if h.get('role') == 'user'])
            except:
                user_msgs = 0

            paused_label = "⏸ PAUSED" if paused else "▶ ACTIVE"
            last_active = last_msg.strftime('%d %b, %I:%M %p') if last_msg else 'Unknown'
            conv_url = f"{RENDER_URL}/conversation/{user_id}?secret={CONTROL_SECRET}"

            report += f"""━━━━━━━━━━━━━━━
📱 +{user_id} {paused_label}
📊 Stage: {status.replace('_', ' ').upper()}
💬 Messages: {user_msgs}
⏰ Last active: {last_active}
🏢 Service: {lead_info.get('service', 'Not identified')}
📝 Business: {lead_info.get('business_name', 'Not provided')}
👤 Name: {lead_info.get('name', 'Not provided')}
<a href="{conv_url}">View Chat</a>

"""
        send_telegram_message(report)

    except Exception as e:
        print(f"Report error: {e}")
        send_telegram_message(f"⚠️ Report error: {e}")
    finally:
        if conn:
            conn.close()

# ============================================================
# DATABASE HELPER FUNCTIONS
# ============================================================

def get_chat_history(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT history FROM whatsapp_chats WHERE user_id = %s;", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return json.loads(row[0]) if row else []
    except Exception as e:
        print(f"Error getting history: {e}")
        return []
    finally:
        if conn:
            conn.close()

def save_chat_history(user_id, history):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO whatsapp_chats (user_id, history, last_message_at, updated_at)
            VALUES (%s, %s, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET
                history = EXCLUDED.history,
                last_message_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP;
        """, (user_id, json.dumps(history)))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error saving history: {e}")
    finally:
        if conn:
            conn.close()

def update_lead_status(user_id, status, lead_info=None):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        if lead_info:
            cursor.execute("""
                UPDATE whatsapp_chats
                SET status = %s, lead_info = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (status, json.dumps(lead_info), user_id))
        else:
            cursor.execute("""
                UPDATE whatsapp_chats
                SET status = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """, (status, user_id))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error updating status: {e}")
    finally:
        if conn:
            conn.close()

def is_bot_paused(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT paused FROM whatsapp_chats WHERE user_id = %s;", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else False
    except Exception as e:
        print(f"Error checking pause: {e}")
        return False
    finally:
        if conn:
            conn.close()

def set_bot_paused(user_id, paused):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO whatsapp_chats (user_id, history, paused, updated_at)
            VALUES (%s, '[]', %s, CURRENT_TIMESTAMP)
            ON CONFLICT (user_id)
            DO UPDATE SET paused = %s, updated_at = CURRENT_TIMESTAMP;
        """, (user_id, paused, paused))
        conn.commit()
        cursor.close()

        status_label = "PAUSED ⏸" if paused else "RESUMED ▶"
        send_telegram_message(
            f"🤖 <b>Bot {status_label}</b>\n📱 +{user_id}\n\n{'<i>You can now handle this conversation manually in Meta Business Suite.</i>' if paused else '<i>AI is now handling this conversation again.</i>'}"
        )

    except Exception as e:
        print(f"Error setting pause: {e}")
    finally:
        if conn:
            conn.close()

def get_conversation_history(user_id):
    return get_chat_history(user_id)

def mark_notified_start(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE whatsapp_chats
            SET notified_start = TRUE, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = %s
        """, (user_id,))
        conn.commit()
        cursor.close()
    except Exception as e:
        print(f"Error marking notification: {e}")
    finally:
        if conn:
            conn.close()

def has_been_notified(user_id):
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT notified_start FROM whatsapp_chats WHERE user_id = %s;", (user_id,))
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else False
    except Exception as e:
        print(f"Error checking notification: {e}")
        return False
    finally:
        if conn:
            conn.close()

# ============================================================
# MAIN AI RESPONSE FUNCTION
# ============================================================

def get_claude_response(user_id, user_message):
    try:
        history = get_chat_history(user_id)
        is_new = not history

        if is_new:
            history.append({
                "role": "user",
                "content": "A new lead has just messaged from a Meta ad about CAC registration or post-registration services in Nigeria."
            })
            history.append({
                "role": "assistant",
                "content": "Understood. I will warmly greet them as Sodiq and guide them naturally toward registration."
            })
            save_chat_history(user_id, history)

            # Notify Sodiq of new lead
            notify_new_lead(user_id)
            mark_notified_start(user_id)

        history.append({
            "role": "user",
            "content": user_message
        })

        if len(history) > 20:
            history = history[-20:]

        response = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=500,
            system=SYSTEM_PROMPT,
            messages=history
        )

        assistant_message = response.content[0].text

        # Detect when all lead details have been collected
        if "[LEAD_READY:" in assistant_message:
            try:
                start = assistant_message.index("[LEAD_READY:") + 12
                end = assistant_message.index("]", start)
                lead_raw = assistant_message[start:end]

                lead_data = {"phone": user_id}
                for item in lead_raw.split("|"):
                    if "=" in item:
                        key, value = item.split("=", 1)
                        lead_data[key.strip()] = value.strip()

                # Notify Sodiq
                notify_lead_ready(user_id, lead_data)

                # Update database
                update_lead_status(user_id, 'lead_ready', lead_data)

                # Remove tag from message before sending to client
                assistant_message = assistant_message[:assistant_message.index("[LEAD_READY:")].strip()

            except Exception as e:
                print(f"Lead extraction error: {e}")
                if "[LEAD_READY:" in assistant_message:
                    assistant_message = assistant_message[:assistant_message.index("[LEAD_READY:")].strip()

        history.append({
            "role": "assistant",
            "content": assistant_message
        })

        save_chat_history(user_id, history)
        return assistant_message

    except Exception as e:
        print(f"Claude API Error: {e}")
        return "Hey! Thanks for reaching out to Degenius Consult LTD. We're having a brief technical issue — someone from the team will respond to you shortly. 🙏"
