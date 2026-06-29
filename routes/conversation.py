from flask import Blueprint, request
from database.connection import DatabaseContext
from config.settings import Config
from utils.security import require_secret
from utils.logger import get_logger

conversation_bp = Blueprint("conversation", __name__)
logger = get_logger("conversation")


@conversation_bp.route("/conversation/<phone>", methods=["GET"])
@require_secret
def view_conversation(phone):
    messages = []
    customer = {}
    fsm_state = "Unknown"

    try:
        with DatabaseContext() as cursor:
            # Get messages
            cursor.execute("""
                SELECT role, content, fsm_state, created_at
                FROM messages WHERE phone = %s
                ORDER BY created_at ASC
            """, (phone,))
            messages = cursor.fetchall()

            # Get customer
            cursor.execute("""
                SELECT full_name, email, service_requested, business_name,
                       nature_of_business, ai_paused, lead_stage
                FROM customers WHERE phone = %s
            """, (phone,))
            row = cursor.fetchone()
            if row:
                customer = {
                    "name": row[0] or "Unknown",
                    "email": row[1] or "Not provided",
                    "service": row[2] or "Not identified",
                    "business": row[3] or "Not provided",
                    "nature": row[4] or "Not provided",
                    "paused": row[5],
                    "stage": row[6] or "unknown",
                }

            # Get FSM state
            cursor.execute(
                "SELECT fsm_state FROM conversations WHERE phone = %s",
                (phone,)
            )
            fsm_row = cursor.fetchone()
            if fsm_row:
                fsm_state = fsm_row[0]

    except Exception as e:
        logger.error(f"Conversation view error: {e}")

    pause_btn = "⏸ Pause Bot" if not customer.get("paused") else "▶ Resume Bot"
    pause_cmd = "PAUSE" if not customer.get("paused") else "RESUME"
    paused_badge = (
        '<span class="badge paused">⏸ PAUSED</span>' if customer.get("paused")
        else '<span class="badge active">▶ AI ACTIVE</span>'
    )

    messages_html = ""
    for msg in messages:
        role, content, state, created_at = msg
        css = "user" if role == "user" else "bot"
        label = "Lead" if role == "user" else "Sodiq (AI)"
        time_str = created_at.strftime('%d %b, %I:%M %p') if created_at else ""
        content_safe = content.replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        messages_html += f"""
        <div class="msg {css}">
            <div class="bubble">
                <div class="msg-label">{label} · {time_str} · {state}</div>
                <div class="msg-text">{content_safe}</div>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Chat +{phone}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:Arial,sans-serif;background:#e5ddd5}}
        .header{{background:#075e54;color:white;padding:15px 20px;position:sticky;top:0;z-index:100}}
        .header h2{{font-size:16px;margin-bottom:4px}}
        .meta{{font-size:12px;opacity:.8;line-height:1.8}}
        .controls{{background:#128c7e;padding:10px 15px;display:flex;gap:8px;flex-wrap:wrap;align-items:center}}
        .btn{{padding:8px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:bold;text-decoration:none;display:inline-block}}
        .btn-back{{background:white;color:#075e54}}
        .btn-pause{{background:#ff6b6b;color:white}}
        .btn-resume{{background:#51cf66;color:white}}
        #notif{{color:white;font-size:12px;padding:5px 0}}
        .chat{{max-width:750px;margin:0 auto;padding:15px;padding-bottom:40px}}
        .msg{{margin:8px 0;display:flex}}
        .msg.user{{justify-content:flex-end}}
        .msg.bot{{justify-content:flex-start}}
        .bubble{{max-width:75%;padding:10px 14px;border-radius:10px}}
        .user .bubble{{background:#dcf8c6;border-radius:10px 0 10px 10px}}
        .bot .bubble{{background:white;border-radius:0 10px 10px 10px}}
        .msg-label{{font-size:10px;color:#888;margin-bottom:4px;font-weight:bold}}
        .msg-text{{font-size:14px;line-height:1.5}}
        .badge{{padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold}}
        .badge.active{{background:#51cf66;color:white}}
        .badge.paused{{background:#ff6b6b;color:white}}
    </style>
</head>
<body>
<div class="header">
    <h2>📱 +{phone} {paused_badge}</h2>
    <div class="meta">
        👤 {customer.get('name')} &nbsp;|&nbsp;
        🏢 {customer.get('service')} &nbsp;|&nbsp;
        📝 {customer.get('business')} &nbsp;|&nbsp;
        📊 {fsm_state}
    </div>
</div>
<div class="controls">
    <a href="/admin?secret={Config.CONTROL_SECRET}" class="btn btn-back">← Admin</a>
    <button class="btn btn-pause" onclick="ctrl('{pause_cmd}')">{pause_btn}</button>
    <span id="notif"></span>
</div>
<div class="chat">
    {messages_html if messages_html else '<p style="text-align:center;color:#666;padding:30px">No messages yet.</p>'}
</div>
<script>
    window.scrollTo(0, document.body.scrollHeight);
    async function ctrl(cmd) {{
        const r = await fetch('/control', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{command: cmd, user_id: '{phone}', secret: '{Config.CONTROL_SECRET}'}})
        }});
        const d = await r.json();
        document.getElementById('notif').textContent = '✅ ' + (d.status || d.error);
        setTimeout(() => location.reload(), 2000);
    }}
</script>
</body>
</html>"""
