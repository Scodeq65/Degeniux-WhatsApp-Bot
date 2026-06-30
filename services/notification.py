from datetime import datetime
from config.settings import Config
from config.business_loader import get_business
from services.telegram import send
from utils.logger import get_logger

logger = get_logger("notification")


def _conv_url(phone: str) -> str:
    return f"{Config.RENDER_URL}/admin/conversation/{phone}"


def _admin_url() -> str:
    return f"{Config.RENDER_URL}/admin"


def notify_new_lead(phone: str):
    biz = get_business()
    msg = f"""🔔 <b>NEW LEAD</b> — {biz.get('company_name', 'Degenius')}

📱 <b>WhatsApp:</b> +{phone}
⏰ <b>Time:</b> {datetime.now().strftime('%d %b %Y, %I:%M %p')}
🤖 <b>Status:</b> AI handling

<a href="{_conv_url(phone)}">📋 View Chat</a> | <a href="{_admin_url()}">⚙️ Admin</a>"""
    result = send(msg)
    logger.info(f"notify_new_lead for +{phone}: {'sent' if result else 'FAILED'}")


def notify_lead_qualified(phone: str, collected: dict):
    msg = f"""🔥 <b>LEAD QUALIFIED — ACTION NEEDED</b>

📱 <b>WhatsApp:</b> +{phone}
👤 <b>Name:</b> {collected.get('customer_name', 'Not provided')}
🏢 <b>Service:</b> {collected.get('service_requested', 'Not provided')}
📝 <b>Business Name:</b> {collected.get('proposed_business_name', 'Not provided')}
🏭 <b>Nature:</b> {collected.get('nature_of_business', 'Not provided')}

⚡ <b>NEXT STEPS:</b>
1️⃣ Run CAC name availability check
2️⃣ Inform lead of result
3️⃣ Collect 20% initial payment

⏸ <i>AI is now paused. Handle manually in Meta Business Suite.</i>

<a href="{_conv_url(phone)}">📋 View Chat</a> | <a href="{_admin_url()}">⚙️ Admin</a>"""
    result = send(msg)
    logger.info(f"notify_lead_qualified for +{phone}: {'sent' if result else 'FAILED'}")


def notify_bot_paused(phone: str):
    msg = (
        f"⏸ <b>Bot PAUSED</b> for +{phone}\n"
        f"<i>Handle this conversation manually in Meta Business Suite.\n"
        f"Resume from Admin Panel when done.</i>\n\n"
        f"<a href='{_conv_url(phone)}'>📋 View Chat</a>"
    )
    send(msg)


def notify_bot_resumed(phone: str):
    msg = f"▶ <b>Bot RESUMED</b> for +{phone}\n<i>AI is handling again.</i>"
    send(msg)


def notify_followup_sent(phone: str, count: int):
    send(f"📤 <b>Follow-up #{count} sent</b> to +{phone}\n<i>Lead inactive for 24+ hours</i>")


def send_daily_report(leads: list):
    if not leads:
        send("📊 <b>Daily Report:</b> No active conversations today.")
        return

    active = [l for l in leads if not l.get("ai_paused")]
    paused = [l for l in leads if l.get("ai_paused")]
    qualified = [l for l in leads if l.get("fsm_state") == "LEAD_QUALIFIED"]

    report = f"""📊 <b>DAILY REPORT — Degenius Consult LTD</b>
📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}

👥 Total Active: {len(leads)}
▶ AI Active: {len(active)}
⏸ Paused: {len(paused)}
🔥 Qualified: {len(qualified)}

"""
    for lead in leads[:10]:
        phone = lead.get("phone", "")
        state = (lead.get("fsm_state") or "").replace("_", " ")
        service = lead.get("service_requested") or "Unknown"
        biz = lead.get("business_name") or "Not provided"
        paused_icon = "⏸" if lead.get("ai_paused") else "▶"
        last = lead.get("last_message_at")
        last_str = last.strftime('%d %b, %I:%M %p') if last else "Unknown"

        report += (
            f"{paused_icon} +{phone}\n"
            f"  {state} | {service} | {biz}\n"
            f"  Last: {last_str}\n"
            f"  <a href='{_conv_url(phone)}'>View</a>\n\n"
        )

    if len(leads) > 10:
        report += f"<i>+{len(leads) - 10} more in <a href='{_admin_url()}'>Admin Panel</a></i>"

    send(report)
