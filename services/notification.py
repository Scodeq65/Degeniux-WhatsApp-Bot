from datetime import datetime
from config.settings import Config
from services.telegram import send
from utils.logger import get_logger

logger = get_logger("notification")

def _conv_url(phone: str) -> str:
    return f"{Config.RENDER_URL}/conversation/{phone}?secret={Config.CONTROL_SECRET}"

def _admin_url() -> str:
    return f"{Config.RENDER_URL}/admin?secret={Config.CONTROL_SECRET}"

def notify_new_lead(phone: str):
    msg = f"""🔔 <b>NEW LEAD</b> — Degenius Consult LTD

📱 <b>WhatsApp:</b> +{phone}
⏰ <b>Time:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
🤖 <b>Status:</b> AI handling conversation

<a href="{_conv_url(phone)}">📋 View Chat</a> | <a href="{_admin_url()}">⚙️ Admin</a>"""
    send(msg)

def notify_lead_qualified(phone: str, collected: dict):
    msg = f"""🔥 <b>LEAD QUALIFIED — ACTION NEEDED!</b>

📱 <b>WhatsApp:</b> +{phone}
👤 <b>Name:</b> {collected.get('customer_name', 'Not provided')}
📧 <b>Email:</b> {collected.get('email_address', 'Not provided')}
🏢 <b>Service:</b> {collected.get('service_requested', 'Not provided')}
📝 <b>Business Name:</b> {collected.get('proposed_business_name', 'Not provided')}
🏭 <b>Nature:</b> {collected.get('nature_of_business', 'Not provided')}

⚡ <b>YOUR NEXT STEPS:</b>
1️⃣ Run CAC name availability check
2️⃣ Reply to lead with result
3️⃣ Collect 20% initial payment

<a href="{_conv_url(phone)}">📋 View Chat</a>

<i>⏸ Pause the bot before replying manually</i>"""
    send(msg)

def notify_followup_sent(phone: str):
    send(f"📤 <b>Follow-up sent to +{phone}</b>\n<i>Lead was inactive for 24+ hours</i>")

def notify_bot_paused(phone: str):
    send(
        f"⏸ <b>Bot PAUSED</b> for +{phone}\n\n"
        f"<i>Handle this conversation manually in Meta Business Suite.\n"
        f"Resume with the admin panel when done.</i>\n\n"
        f"<a href='{_conv_url(phone)}'>📋 View Chat</a>"
    )

def notify_bot_resumed(phone: str):
    send(
        f"▶ <b>Bot RESUMED</b> for +{phone}\n"
        f"<i>AI is handling this conversation again.</i>"
    )

def send_daily_report(leads: list):
    if not leads:
        send("📊 <b>Daily Report:</b> No active conversations today.")
        return

    active = [l for l in leads if not l.get('ai_paused')]
    paused = [l for l in leads if l.get('ai_paused')]
    qualified = [l for l in leads if l.get('fsm_state') == 'LEAD_QUALIFIED']

    report = f"""📊 <b>DAILY REPORT — DEGENIUS CONSULT LTD</b>
📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}

👥 Total Leads: {len(leads)}
▶ AI Active: {len(active)}
⏸ Paused (Human): {len(paused)}
🔥 Qualified (Need Action): {len(qualified)}

"""
    for lead in leads[:15]:
        phone = lead.get('phone', '')
        state = lead.get('fsm_state', '').replace('_', ' ')
        service = lead.get('service_requested', 'Unknown')
        biz = lead.get('proposed_business_name', 'Unknown')
        paused_label = "⏸" if lead.get('ai_paused') else "▶"
        last = lead.get('last_customer_message_at', '')
        if last:
            try:
                last = last.strftime('%d %b, %I:%M %p')
            except:
                pass

        report += f"""{paused_label} +{phone}
  Stage: {state} | Service: {service}
  Business: {biz} | Last: {last}
  <a href="{_conv_url(phone)}">View</a>

"""
    if len(leads) > 15:
        report += f"<i>...and {len(leads) - 15} more. <a href='{_admin_url()}'>View all in Admin</a></i>"

    send(report)
