from flask import Blueprint, request, session, redirect, render_template_string
from database.models import get_all_active_leads
from config.settings import Config
from utils.security import require_admin
from utils.security import verify_control_secret
from utils.validators import sanitize_html
from utils.logger import get_logger
from datetime import datetime

admin_bp = Blueprint("admin", __name__)
logger = get_logger("admin")

# ── Login page ──────────────────────────────────────────────

LOGIN_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:Arial,sans-serif;background:linear-gradient(135deg,#075e54,#128c7e);
             display:flex;justify-content:center;align-items:center;min-height:100vh}
        .card{background:white;padding:40px;border-radius:16px;width:340px;
              box-shadow:0 8px 32px rgba(0,0,0,.25);text-align:center}
        .logo{font-size:40px;margin-bottom:10px}
        h2{color:#075e54;font-size:20px;margin-bottom:6px}
        p{color:#888;font-size:13px;margin-bottom:24px}
        input{width:100%;padding:13px;border:2px solid #e0e0e0;border-radius:8px;
              font-size:15px;margin-bottom:12px;outline:none;transition:border-color .2s}
        input:focus{border-color:#075e54}
        button{width:100%;padding:13px;background:#075e54;color:white;border:none;
               border-radius:8px;font-size:15px;font-weight:bold;cursor:pointer;transition:background .2s}
        button:hover{background:#128c7e}
        .error{color:#e53e3e;font-size:13px;margin-bottom:12px;
               background:#fff5f5;padding:8px;border-radius:6px}
    </style>
</head>
<body>
<div class="card">
    <div class="logo">🏢</div>
    <h2>Degenius Admin</h2>
    <p>WhatsApp AI Agent Dashboard</p>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <form method="POST">
        <input type="password" name="password" placeholder="Enter access code" autofocus required>
        <button type="submit">Login</button>
    </form>
</div>
</body>
</html>"""

# ── Dashboard ────────────────────────────────────────────────

DASHBOARD_HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin</title>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="refresh" content="60">
    <style>
        *{box-sizing:border-box;margin:0;padding:0}
        body{font-family:Arial,sans-serif;background:#f5f7fb;color:#333}
        .topbar{background:#075e54;color:white;padding:14px 24px;display:flex;
                justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100;
                box-shadow:0 2px 8px rgba(0,0,0,.2)}
        .topbar h1{font-size:17px}
        .topbar-right{display:flex;gap:12px;align-items:center;font-size:13px}
        .logout{background:rgba(255,255,255,.15);padding:6px 14px;border-radius:6px;
                color:white;text-decoration:none;font-size:13px}
        .stats{display:flex;gap:16px;padding:20px 24px;flex-wrap:wrap;background:#075e54}
        .stat{background:rgba(255,255,255,.12);color:white;padding:14px 20px;
              border-radius:10px;min-width:110px;text-align:center;flex:1}
        .stat .n{font-size:30px;font-weight:bold;margin-bottom:4px}
        .stat .l{font-size:11px;opacity:.85;text-transform:uppercase;letter-spacing:.5px}
        .container{max-width:960px;margin:24px auto;padding:0 16px}
        .section-title{font-size:12px;font-weight:bold;color:#888;
                       text-transform:uppercase;letter-spacing:.6px;margin-bottom:14px}
        .card{background:white;border-radius:12px;padding:16px 20px;margin-bottom:12px;
              box-shadow:0 1px 4px rgba(0,0,0,.08);border-left:4px solid #e0e0e0}
        .card.qualified{border-left-color:#f6ad55}
        .card.paused{border-left-color:#fc8181}
        .card.active{border-left-color:#68d391}
        .card-header{display:flex;justify-content:space-between;align-items:center;
                     margin-bottom:10px;flex-wrap:wrap;gap:8px}
        .phone{font-weight:bold;font-size:15px}
        .badges{display:flex;gap:6px;flex-wrap:wrap}
        .badge{padding:3px 10px;border-radius:20px;font-size:11px;font-weight:bold;color:white}
        .badge-active{background:#48bb78}
        .badge-paused{background:#f56565}
        .badge-qualified{background:#ed8936}
        .badge-state{background:#718096;color:white}
        .card-info{display:flex;gap:16px;font-size:12px;color:#666;margin-bottom:12px;flex-wrap:wrap}
        .card-info span{display:flex;align-items:center;gap:4px}
        .actions{display:flex;gap:8px;flex-wrap:wrap}
        .btn{padding:7px 14px;border:none;border-radius:7px;cursor:pointer;
             font-size:12px;font-weight:bold;text-decoration:none;display:inline-block;transition:opacity .2s}
        .btn:hover{opacity:.85}
        .btn-view{background:#075e54;color:white}
        .btn-pause{background:#f56565;color:white}
        .btn-resume{background:#48bb78;color:white}
        .empty{text-align:center;color:#aaa;padding:40px;font-size:15px}
        #toast{position:fixed;bottom:20px;right:20px;background:#2d3748;color:white;
               padding:12px 20px;border-radius:8px;display:none;font-size:13px;
               box-shadow:0 4px 12px rgba(0,0,0,.3);z-index:999}
    </style>
</head>
<body>
<div class="topbar">
    <h1>🏢 Degenius Consult LTD — Admin</h1>
    <div class="topbar-right">
        <span>{{ now }}</span>
        <a href="/admin/logout" class="logout">Logout</a>
    </div>
</div>

<div class="stats">
    <div class="stat"><div class="n">{{ stats.total }}</div><div class="l">Total Leads</div></div>
    <div class="stat"><div class="n">{{ stats.active }}</div><div class="l">AI Active</div></div>
    <div class="stat"><div class="n">{{ stats.paused }}</div><div class="l">Paused</div></div>
    <div class="stat"><div class="n">{{ stats.qualified }}</div><div class="l">🔥 Qualified</div></div>
    <div class="stat"><div class="n">{{ stats.completed }}</div><div class="l">✅ Completed</div></div>
</div>

<div class="container">
    <div class="section-title">Active Conversations</div>

    {% if leads %}
        {% for lead in leads %}
        {% set state = lead.fsm_state or '' %}
        {% set card_class = 'paused' if lead.ai_paused else ('qualified' if state == 'LEAD_QUALIFIED' else 'active') %}
        <div class="card {{ card_class }}">
            <div class="card-header">
                <div>
                    <span class="phone">📱 +{{ lead.phone }}</span>
                </div>
                <div class="badges">
                    {% if lead.ai_paused %}
                        <span class="badge badge-paused">⏸ PAUSED</span>
                    {% else %}
                        <span class="badge badge-active">▶ AI ACTIVE</span>
                    {% endif %}
                    {% if lead.notified_qualified %}
                        <span class="badge badge-qualified">🔥 QUALIFIED</span>
                    {% endif %}
                    <span class="badge badge-state">{{ state.replace('_',' ') }}</span>
                </div>
            </div>
            <div class="card-info">
                <span>👤 {{ lead.full_name or 'Unknown' }}</span>
                <span>🏢 {{ lead.service_requested or 'Not identified' }}</span>
                <span>📝 {{ lead.business_name or 'Not provided' }}</span>
                <span>💬 {{ lead.total_messages or 0 }} messages</span>
                <span>⏰ {{ lead.last_str }}</span>
            </div>
            <div class="actions">
                <a href="/admin/conversation/{{ lead.phone }}" class="btn btn-view">💬 View Chat</a>
                {% if lead.ai_paused %}
                    <button class="btn btn-resume" onclick="ctrl('RESUME','{{ lead.phone }}')">▶ Resume AI</button>
                {% else %}
                    <button class="btn btn-pause" onclick="ctrl('PAUSE','{{ lead.phone }}')">⏸ Pause AI</button>
                {% endif %}
            </div>
        </div>
        {% endfor %}
    {% else %}
        <div class="empty">No conversations yet. Leads will appear here as they come in. 🚀</div>
    {% endif %}
</div>

<div id="toast"></div>

<script>
const SECRET = "{{ secret }}";
async function ctrl(cmd, phone) {
    try {
        const r = await fetch('/admin/control', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({command: cmd, user_id: phone, secret: SECRET})
        });
        const d = await r.json();
        toast(d.status || d.error);
        setTimeout(() => location.reload(), 2000);
    } catch(e) { toast('Error: ' + e.message); }
}
function toast(msg) {
    const t = document.getElementById('toast');
    t.textContent = msg;
    t.style.display = 'block';
    setTimeout(() => t.style.display = 'none', 3000);
}
</script>
</body>
</html>"""


@admin_bp.route("/admin/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        pwd = request.form.get("password", "")
        if verify_control_secret(pwd):
            session["admin_authenticated"] = True
            session.permanent = True
            logger.info(f"Admin login from {request.remote_addr}")
            return redirect("/admin")
        error = "Incorrect access code. Please try again."
        logger.warning(f"Failed admin login from {request.remote_addr}")
    return render_template_string(LOGIN_HTML, error=error)


@admin_bp.route("/admin/logout")
def logout():
    session.clear()
    return redirect("/admin/login")


@admin_bp.route("/admin")
@require_admin
def dashboard():
    leads = get_all_active_leads()

    stats = {
        "total": len(leads),
        "active": len([l for l in leads if not l.get("ai_paused")]),
        "paused": len([l for l in leads if l.get("ai_paused")]),
        "qualified": len([l for l in leads if l.get("notified_qualified")]),
        "completed": len([l for l in leads if l.get("fsm_state") == "COMPLETED"]),
    }

    for lead in leads:
        lm = lead.get("last_message_at")
        lead["last_str"] = lm.strftime('%d %b, %I:%M %p') if lm else "No messages"

    return render_template_string(
        DASHBOARD_HTML,
        leads=leads,
        stats=stats,
        now=datetime.now().strftime('%d %b %Y, %I:%M %p'),
        secret=Config.CONTROL_SECRET
    )
