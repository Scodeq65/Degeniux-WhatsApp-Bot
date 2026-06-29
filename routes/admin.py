from flask import Blueprint, request
from database.connection import DatabaseContext
from config.settings import Config
from utils.security import require_secret
from utils.logger import get_logger
import json

admin_bp = Blueprint("admin", __name__)
logger = get_logger("admin")


@admin_bp.route("/admin", methods=["GET"])
def admin():
    secret = request.args.get("secret", "")

    if not secret or secret != Config.CONTROL_SECRET:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        body{{font-family:Arial;display:flex;justify-content:center;align-items:center;min-height:100vh;background:#075e54;margin:0}}
        .box{{background:white;padding:35px;border-radius:12px;text-align:center;width:320px;box-shadow:0 4px 20px rgba(0,0,0,.3)}}
        h2{{color:#075e54;margin-bottom:25px;font-size:20px}}
        input{{padding:12px;width:100%;border:1px solid #ddd;border-radius:8px;margin-bottom:12px;font-size:14px}}
        button{{background:#075e54;color:white;padding:12px;width:100%;border:none;border-radius:8px;cursor:pointer;font-size:15px;font-weight:bold}}
        button:hover{{background:#128c7e}}
    </style>
</head>
<body>
<div class="box">
    <h2>🔐 Degenius Admin</h2>
    <form onsubmit="login(event)">
        <input type="password" id="pwd" placeholder="Access code" autofocus>
        <button type="submit">Login</button>
    </form>
</div>
<script>
function login(e){{e.preventDefault();window.location.href='/admin?secret='+document.getElementById('pwd').value}}
</script>
</body>
</html>"""

    leads = []
    stats = {"total": 0, "active": 0, "paused": 0, "qualified": 0, "completed": 0}

    try:
        with DatabaseContext() as cursor:
            cursor.execute("""
                SELECT c.phone, c.full_name, c.service_requested, c.business_name,
                       c.lead_stage, c.ai_paused, c.last_customer_message_at,
                       cv.fsm_state, cv.total_messages, cv.notified_qualified
                FROM customers c
                LEFT JOIN conversations cv ON c.phone = cv.phone
                ORDER BY c.last_customer_message_at DESC NULLS LAST
                LIMIT 100
            """)
            leads = cursor.fetchall()

            stats["total"] = len(leads)
            stats["active"] = len([l for l in leads if not l[5]])
            stats["paused"] = len([l for l in leads if l[5]])
            stats["qualified"] = len([l for l in leads if l[7] == 'LEAD_QUALIFIED'])
            stats["completed"] = len([l for l in leads if l[7] == 'COMPLETED'])

    except Exception as e:
        logger.error(f"Admin load error: {e}")

    leads_html = ""
    for lead in leads:
        phone, name, service, biz, stage, paused, last_msg, fsm_state, msg_count, notified = lead
        paused_color = "#ff6b6b" if paused else "#51cf66"
        paused_label = "⏸ PAUSED" if paused else "▶ ACTIVE"
        stage_display = (fsm_state or stage or "unknown").replace("_", " ").upper()
        last_active = last_msg.strftime('%d %b, %I:%M %p') if last_msg else 'No messages yet'
        conv_url = f"/conversation/{phone}?secret={Config.CONTROL_SECRET}"
        qualified_badge = ' 🔥' if notified else ''

        leads_html += f"""
<div class="card">
    <div class="card-top">
        <div>
            <span class="phone">📱 +{phone}</span>
            <span class="badge" style="background:{paused_color}">{paused_label}</span>
            {qualified_badge}
        </div>
        <span class="stage">{stage_display}</span>
    </div>
    <div class="card-info">
        <span>👤 {name or 'Unknown'}</span>
        <span>🏢 {service or 'Not identified'}</span>
        <span>📝 {biz or 'Not provided'}</span>
        <span>💬 {msg_count or 0} messages</span>
        <span>⏰ {last_active}</span>
    </div>
    <div class="card-actions">
        <a href="{conv_url}" class="btn btn-view">💬 View Chat</a>
        <button class="btn btn-pause" onclick="ctrl('PAUSE','{phone}')">⏸ Pause</button>
        <button class="btn btn-resume" onclick="ctrl('RESUME','{phone}')">▶ Resume</button>
    </div>
</div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin Panel</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        *{{box-sizing:border-box;margin:0;padding:0}}
        body{{font-family:Arial,sans-serif;background:#f0f2f5}}
        .header{{background:#075e54;color:white;padding:20px 25px}}
        .header h1{{font-size:20px;margin-bottom:5px}}
        .header p{{font-size:13px;opacity:.8}}
        .stats{{display:flex;gap:15px;padding:20px 25px;flex-wrap:wrap;background:#128c7e}}
        .stat{{background:rgba(255,255,255,.15);color:white;padding:12px 20px;border-radius:10px;text-align:center;min-width:100px}}
        .stat .num{{font-size:28px;font-weight:bold}}
        .stat .lbl{{font-size:11px;opacity:.9;margin-top:3px}}
        .container{{max-width:900px;margin:20px auto;padding:0 15px}}
        .section-title{{font-size:13px;font-weight:bold;color:#666;margin-bottom:12px;text-transform:uppercase;letter-spacing:.5px}}
        .card{{background:white;border-radius:10px;padding:15px;margin:10px 0;box-shadow:0 1px 4px rgba(0,0,0,.1)}}
        .card-top{{display:flex;justify-content:space-between;align-items:center;margin-bottom:10px;flex-wrap:wrap;gap:8px}}
        .phone{{font-weight:bold;font-size:15px;margin-right:8px}}
        .badge{{color:white;padding:3px 10px;border-radius:12px;font-size:11px;font-weight:bold}}
        .stage{{font-size:11px;color:#666;background:#f0f2f5;padding:3px 8px;border-radius:8px}}
        .card-info{{display:flex;gap:12px;font-size:12px;color:#555;margin-bottom:12px;flex-wrap:wrap}}
        .card-actions{{display:flex;gap:8px;flex-wrap:wrap}}
        .btn{{padding:7px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;font-weight:bold;text-decoration:none;display:inline-block}}
        .btn-view{{background:#075e54;color:white}}
        .btn-pause{{background:#ff6b6b;color:white}}
        .btn-resume{{background:#51cf66;color:white}}
        #toast{{position:fixed;top:15px;right:15px;background:#333;color:white;padding:12px 20px;border-radius:8px;display:none;font-size:13px;z-index:999;box-shadow:0 3px 10px rgba(0,0,0,.3)}}
    </style>
</head>
<body>
<div class="header">
    <h1>🏢 Degenius Consult LTD</h1>
    <p>WhatsApp AI Agent — Admin Panel</p>
</div>
<div class="stats">
    <div class="stat"><div class="num">{stats['total']}</div><div class="lbl">Total Leads</div></div>
    <div class="stat"><div class="num">{stats['active']}</div><div class="lbl">AI Active</div></div>
    <div class="stat"><div class="num">{stats['paused']}</div><div class="lbl">Paused</div></div>
    <div class="stat"><div class="num">{stats['qualified']}</div><div class="lbl">🔥 Qualified</div></div>
    <div class="stat"><div class="num">{stats['completed']}</div><div class="lbl">✅ Completed</div></div>
</div>
<div class="container">
    <div class="section-title">Recent Conversations</div>
    {leads_html if leads_html else '<p style="color:#666;text-align:center;padding:30px">No conversations yet.</p>'}
</div>
<div id="toast"></div>
<script>
async function ctrl(cmd, phone) {{
    const r = await fetch('/control', {{
        method: 'POST',
        headers: {{'Content-Type':'application/json'}},
        body: JSON.stringify({{command:cmd, user_id:phone, secret:'{Config.CONTROL_SECRET}'}})
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
