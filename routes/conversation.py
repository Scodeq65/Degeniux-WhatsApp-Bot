from flask import Blueprint, redirect
from database.connection import DB
from database.models import get_customer
from config.settings import Config
from utils.security import require_admin
from utils.validators import sanitize_html
from utils.logger import get_logger

conversation_bp = Blueprint("conversation", __name__)
logger = get_logger("conversation")


@conversation_bp.route("/admin/conversation/<phone>")
@require_admin
def view(phone):
    messages = []
    customer = {}
    fsm_state = "Unknown"
    collected = {}

    try:
        with DB() as c:
            c.execute("""
                SELECT role, content, fsm_state, created_at
                FROM messages WHERE phone = %s
                ORDER BY created_at ASC
            """, (phone,))
            messages = c.fetchall()

            c.execute("""
                SELECT full_name, service_requested, business_name,
                       nature_of_business, ai_paused
                FROM customers WHERE phone = %s
            """, (phone,))
            row = c.fetchone()
            if row:
                customer = {
                    "name": row[0] or "Unknown",
                    "service": row[1] or "Not identified",
                    "business": row[2] or "Not provided",
                    "nature": row[3] or "Not provided",
                    "paused": row[4],
                }

            c.execute("SELECT fsm_state, collected_fields FROM conversations WHERE phone = %s", (phone,))
            row2 = c.fetchone()
            if row2:
                fsm_state = row2[0] or "Unknown"
                collected = dict(row2[1]) if row2[1] else {}

    except Exception as e:
        logger.error(f"Conversation view error: {e}")

    paused = customer.get("paused", False)
    toggle_cmd = "RESUME" if paused else "PAUSE"
    toggle_label = "▶ Resume AI" if paused else "⏸ Pause AI"
    toggle_color = "#48bb78" if paused else "#f56565"
    status_badge = (
        '<span style="background:#f56565;color:white;padding:3px 10px;border-radius:12px;font-size:11px">⏸ PAUSED</span>'
        if paused else
        '<span style="background:#48bb78;color:white;padding:3px 10px;border-radius:12px;font-size:11px">▶ AI ACTIVE</span>'
    )

    msgs_html = ""
    for msg in messages:
        role, content, state, created_at = msg
        css = "user" if role == "user" else "bot"
        label = "Lead" if role == "user" else "Sodiq (AI)"
        time_str = created_at.strftime('%d %b, %I:%M %p') if created_at else ""
        safe_content = sanitize_html(content).replace("\n", "<br>")
        msgs_html += f"""
<div class="msg {css}">
  <div class="bubble">
    <div class="msg-meta">{label} · {time_str}</div>
    <div class="msg-text">{safe_content}</div>
  </div>
</div>"""

    collected_html = ""
    labels = {
        "customer_name": "Name",
        "service_requested": "Service",
        "proposed_business_name": "Business Name",
        "nature_of_business": "Nature",
    }
    for k, v in collected.items():
        if v:
            collected_html += f"<div class='info-item'><span class='info-label'>{labels.get(k, k)}</span><span class='info-value'>{sanitize_html(str(v))}</span></div>"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Chat +{phone}</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:Arial,sans-serif;background:#e5ddd5;display:flex;flex-direction:column;height:100vh}}
        .topbar{{background:#075e54;color:white;padding:12px 16px;display:flex;
                 justify-content:space-between;align-items:center;flex-shrink:0}}
        .topbar-left a{{color:rgba(255,255,255,.8);text-decoration:none;font-size:13px;margin-right:10px}}
        .topbar h2{{font-size:15px;margin-bottom:3px}}
        .topbar p{{font-size:11px;opacity:.8}}
        .controls{{background:#128c7e;padding:10px 14px;display:flex;gap:8px;flex-wrap:wrap;flex-shrink:0}}
        .btn{{padding:7px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;
              font-weight:bold;text-decoration:none;display:inline-block}}
        .info-panel{{background:white;padding:12px 16px;border-bottom:1px solid #e0e0e0;flex-shrink:0}}
        .info-panel h3{{font-size:12px;color:#888;text-transform:uppercase;margin-bottom:8px}}
        .info-grid{{display:flex;gap:16px;flex-wrap:wrap}}
        .info-item{{display:flex;flex-direction:column;font-size:12px}}
        .info-label{{color:#888;font-size:10px;text-transform:uppercase;margin-bottom:2px}}
        .info-value{{color:#333;font-weight:bold}}
        .chat{{flex:1;overflow-y:auto;padding:12px;}}
        .msg{{margin:6px 0;display:flex}}
        .msg.user{{justify-content:flex-end}}
        .msg.bot{{justify-content:flex-start}}
        .bubble{{max-width:76%;padding:10px 14px;border-radius:10px}}
        .user .bubble{{background:#dcf8c6;border-radius:10px 0 10px 10px}}
        .bot .bubble{{background:white;border-radius:0 10px 10px 10px;box-shadow:0 1px 2px rgba(0,0,0,.1)}}
        .msg-meta{{font-size:10px;color:#aaa;margin-bottom:4px}}
        .msg-text{{font-size:14px;line-height:1.5}}
        #toast{{position:fixed;bottom:20px;right:20px;background:#2d3748;color:white;
                padding:10px 18px;border-radius:8px;display:none;font-size:13px;z-index:999}}
    </style>
</head>
<body>
<div class="topbar">
    <div>
        <div class="topbar-left"><a href="/admin">← Dashboard</a></div>
        <h2>📱 +{phone} {status_badge}</h2>
        <p>Stage: {fsm_state.replace('_',' ')}</p>
    </div>
</div>
<div class="controls">
    <button class="btn" style="background:{toggle_color};color:white"
            onclick="ctrl('{toggle_cmd}')">{toggle_label}</button>
    <span style="color:white;font-size:12px;align-self:center">Service: {customer.get('service','?')} | Business: {customer.get('business','?')}</span>
</div>
{'<div class="info-panel"><h3>Lead Profile</h3><div class="info-grid">' + collected_html + '</div></div>' if collected_html else ''}
<div class="chat">
    {msgs_html if msgs_html else '<p style="text-align:center;color:#aaa;padding:30px">No messages yet.</p>'}
</div>
<div id="toast"></div>
<script>
    window.scrollTo(0, document.body.scrollHeight);
    const SECRET = "{Config.CONTROL_SECRET}";
    async function ctrl(cmd) {{
        const r = await fetch('/admin/control', {{
            method: 'POST',
            headers: {{'Content-Type': 'application/json'}},
            body: JSON.stringify({{command: cmd, user_id: '{phone}', secret: SECRET}})
        }});
        const d = await r.json();
        const t = document.getElementById('toast');
        t.textContent = d.status || d.error;
        t.style.display = 'block';
        setTimeout(() => {{t.style.display='none'; location.reload()}}, 2500);
    }}
</script>
</body>
</html>"""
