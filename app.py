from flask import Flask, request, jsonify
import requests
import json
import os
import atexit
from claude_agent import (
    get_claude_response,
    is_bot_paused,
    set_bot_paused,
    get_conversation_history,
    check_and_send_followups,
    send_3day_reports,
    get_db_connection
)
from apscheduler.schedulers.background import BackgroundScheduler

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")
CONTROL_SECRET = os.environ.get("CONTROL_SECRET", "degenius_control_2024")
RENDER_URL = os.environ.get("RENDER_URL", "https://degeniux-whatsapp-bot.onrender.com")

# ============================================================
# SCHEDULER — Follow-ups every hour, Report daily at 8AM
# ============================================================
scheduler = BackgroundScheduler()
scheduler.add_job(check_and_send_followups, 'interval', hours=1, id='followup_job')
scheduler.add_job(send_3day_reports, 'cron', hour=7, minute=0, id='report_job')
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

# ============================================================
# WHATSAPP MESSAGING
# ============================================================

def send_whatsapp_message(to, message):
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
        response = requests.post(url, headers=headers, json=data)
        print(f"WhatsApp Status: {response.status_code}")
        print(f"WhatsApp Response: {response.text}")
        return response
    except Exception as e:
        print(f"WhatsApp error: {e}")
        return None

# ============================================================
# ROUTES
# ============================================================

@app.route("/", methods=["GET"])
def home():
    return "Degenius WhatsApp Bot is running! ✅", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"Incoming: {json.dumps(data, indent=2)}")

    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "statuses" in value:
            return "OK", 200

        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            message_type = message["type"]

            print(f"From: {from_number}, Type: {message_type}")

            # Check if bot is paused for this user
            if is_bot_paused(from_number):
                print(f"Bot paused for {from_number} — skipping AI")
                return "OK", 200

            if message_type == "text":
                user_message = message["text"]["body"]
                ai_response = get_claude_response(from_number, user_message)
                send_whatsapp_message(from_number, ai_response)

            elif message_type == "image":
                send_whatsapp_message(
                    from_number,
                    "Thanks for sending that! For registration purposes, kindly type out the details you need help with and I'll assist you right away. 😊"
                )

            elif message_type == "audio":
                send_whatsapp_message(
                    from_number,
                    "Hey! I noticed you sent a voice note. Kindly type out what you need and I'll help you immediately. 😊"
                )

            elif message_type == "document":
                send_whatsapp_message(
                    from_number,
                    "Thanks for sending that! Our team will review it shortly. Is there anything else I can help you with? 😊"
                )

            else:
                send_whatsapp_message(
                    from_number,
                    "Hey! Thanks for reaching out to Degenius Consult LTD. Kindly type your message and I'll be happy to help. 😊"
                )

    except KeyError as e:
        print(f"KeyError: {e}")
    except Exception as e:
        import traceback
        print(f"Error: {traceback.format_exc()}")

    return "OK", 200

# ============================================================
# BOT CONTROL — PAUSE / RESUME
# ============================================================

@app.route("/control", methods=["POST"])
def control_bot():
    data = request.get_json()
    command = data.get("command", "").upper()
    user_id = data.get("user_id", "")
    secret = data.get("secret", "")

    if secret != CONTROL_SECRET:
        return jsonify({"error": "Unauthorized"}), 401

    if not user_id:
        return jsonify({"error": "user_id required"}), 400

    if command == "PAUSE":
        set_bot_paused(user_id, True)
        return jsonify({"status": f"Bot paused for +{user_id}"}), 200

    elif command == "RESUME":
        set_bot_paused(user_id, False)
        return jsonify({"status": f"Bot resumed for +{user_id}"}), 200

    return jsonify({"error": "Invalid command. Use PAUSE or RESUME"}), 400

# ============================================================
# CONVERSATION VIEWER
# ============================================================

@app.route("/conversation/<user_id>", methods=["GET"])
def view_conversation(user_id):
    secret = request.args.get("secret", "")
    if secret != CONTROL_SECRET:
        return "Unauthorized", 401

    history = get_conversation_history(user_id)
    if not history:
        return f"No conversation found for +{user_id}", 404

    # Filter out system context messages (first 2)
    filtered = [m for m in history if m.get("role") in ["user", "assistant"]]
    if len(filtered) > 2:
        filtered = filtered[2:]

    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Chat — +{user_id}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: Arial, sans-serif; background: #e5ddd5; }}
        .header {{ background: #075e54; color: white; padding: 15px 20px; position: sticky; top: 0; z-index: 100; }}
        .header h2 {{ font-size: 16px; }}
        .header p {{ font-size: 12px; opacity: 0.8; margin-top: 3px; }}
        .controls {{ background: #128c7e; padding: 10px 15px; display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
        .btn {{ padding: 7px 14px; border: none; border-radius: 5px; cursor: pointer; font-size: 13px; font-weight: bold; }}
        .btn-pause {{ background: #ff6b6b; color: white; }}
        .btn-resume {{ background: #51cf66; color: white; }}
        .btn-back {{ background: white; color: #075e54; text-decoration: none; display: inline-block; }}
        #status {{ color: white; font-size: 12px; }}
        .chat {{ max-width: 800px; margin: 0 auto; padding: 15px; }}
        .msg {{ margin: 6px 0; display: flex; }}
        .msg.user {{ justify-content: flex-end; }}
        .msg.assistant {{ justify-content: flex-start; }}
        .bubble {{ max-width: 78%; padding: 8px 12px; border-radius: 8px; font-size: 14px; line-height: 1.5; }}
        .user .bubble {{ background: #dcf8c6; border-radius: 8px 0 8px 8px; }}
        .assistant .bubble {{ background: white; border-radius: 0 8px 8px 8px; }}
        .label {{ font-size: 11px; color: #888; margin-bottom: 3px; font-weight: bold; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>Degenius Consult LTD</h2>
        <p>Conversation with +{user_id}</p>
    </div>
    <div class="controls">
        <a href="/admin?secret={CONTROL_SECRET}" class="btn btn-back">← Admin</a>
        <button class="btn btn-pause" onclick="ctrl('PAUSE')">⏸ Pause Bot</button>
        <button class="btn btn-resume" onclick="ctrl('RESUME')">▶ Resume Bot</button>
        <span id="status"></span>
    </div>
    <div class="chat">"""

    for msg in filtered:
        role = msg.get("role", "")
        content = msg.get("content", "").replace("\n", "<br>")
        css = "user" if role == "user" else "assistant"
        label = "Lead" if role == "user" else "Sodiq (AI)"
        html += f"""
        <div class="msg {css}">
            <div class="bubble">
                <div class="label">{label}</div>
                {content}
            </div>
        </div>"""

    html += f"""
    </div>
    <script>
        window.scrollTo(0, document.body.scrollHeight);
        async function ctrl(cmd) {{
            const r = await fetch('/control', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{command: cmd, user_id: '{user_id}', secret: '{CONTROL_SECRET}'}})
            }});
            const d = await r.json();
            document.getElementById('status').textContent = '✅ ' + (d.status || d.error);
        }}
    </script>
</body>
</html>"""
    return html

# ============================================================
# ADMIN PANEL
# ============================================================

@app.route("/admin", methods=["GET"])
def admin():
    secret = request.args.get("secret", "")

    if secret != CONTROL_SECRET:
        return """<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body { font-family: Arial; display: flex; justify-content: center; align-items: center; min-height: 100vh; background: #075e54; margin: 0; }
        .box { background: white; padding: 30px; border-radius: 10px; text-align: center; width: 300px; }
        h2 { color: #075e54; margin-bottom: 20px; }
        input { padding: 10px; width: 100%; border: 1px solid #ccc; border-radius: 5px; margin-bottom: 10px; font-size: 14px; }
        button { background: #075e54; color: white; padding: 10px; width: 100%; border: none; border-radius: 5px; cursor: pointer; font-size: 14px; }
    </style>
</head>
<body>
<div class="box">
    <h2>🔐 Degenius Admin</h2>
    <form onsubmit="login(event)">
        <input type="password" id="pwd" placeholder="Enter access code">
        <button type="submit">Login</button>
    </form>
</div>
<script>
function login(e) {
    e.preventDefault();
    window.location.href = '/admin?secret=' + document.getElementById('pwd').value;
}
</script>
</body>
</html>"""

    # Load all conversations
    conn = None
    leads = []
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_id, status, paused, lead_info, last_message_at, history
            FROM whatsapp_chats
            ORDER BY last_message_at DESC
            LIMIT 100
        """)
        leads = cursor.fetchall()
        cursor.close()
    except Exception as e:
        print(f"Admin load error: {e}")
    finally:
        if conn:
            conn.close()

    leads_html = ""
    for lead in leads:
        user_id, status, paused, lead_info_str, last_msg, history_str = lead
        try:
            lead_info = json.loads(lead_info_str) if lead_info_str else {}
        except:
            lead_info = {}
        try:
            history = json.loads(history_str) if history_str else []
            msg_count = len([h for h in history if h.get('role') == 'user'])
        except:
            msg_count = 0

        paused_bg = "#ff6b6b" if paused else "#51cf66"
        paused_label = "⏸ PAUSED" if paused else "▶ ACTIVE"
        last_active = last_msg.strftime('%d %b, %I:%M %p') if last_msg else 'Unknown'
        conv_url = f"/conversation/{user_id}?secret={CONTROL_SECRET}"

        leads_html += f"""
        <div class="card">
            <div class="card-header">
                <span class="phone">📱 +{user_id}</span>
                <span class="badge" style="background:{paused_bg}">{paused_label}</span>
            </div>
            <div class="card-info">
                <span>📊 {status.replace('_',' ').upper()}</span>
                <span>🏢 {lead_info.get('service','Not identified')}</span>
                <span>📝 {lead_info.get('business_name','Not provided')}</span>
                <span>👤 {lead_info.get('name','Not provided')}</span>
                <span>💬 {msg_count} messages</span>
                <span>⏰ {last_active}</span>
            </div>
            <div class="card-actions">
                <a href="{conv_url}" class="btn btn-view">💬 View Chat</a>
                <button class="btn btn-pause" onclick="ctrl('PAUSE','{user_id}')">⏸ Pause</button>
                <button class="btn btn-resume" onclick="ctrl('RESUME','{user_id}')">▶ Resume</button>
            </div>
        </div>"""

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Degenius Admin Panel</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ font-family: Arial; background: #f0f2f5; }}
        .header {{ background: #075e54; color: white; padding: 20px; }}
        .header h2 {{ font-size: 18px; }}
        .header p {{ font-size: 13px; opacity: 0.8; margin-top: 5px; }}
        .container {{ max-width: 900px; margin: 20px auto; padding: 0 15px; }}
        .summary {{ background: white; border-radius: 10px; padding: 15px 20px; margin-bottom: 20px; display: flex; gap: 20px; flex-wrap: wrap; }}
        .summary-item {{ text-align: center; }}
        .summary-item .num {{ font-size: 24px; font-weight: bold; color: #075e54; }}
        .summary-item .lbl {{ font-size: 12px; color: #666; }}
        .card {{ background: white; border-radius: 10px; padding: 15px; margin: 10px 0; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        .card-header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px; }}
        .phone {{ font-weight: bold; font-size: 15px; }}
        .badge {{ color: white; padding: 3px 10px; border-radius: 12px; font-size: 12px; }}
        .card-info {{ display: flex; gap: 12px; font-size: 12px; color: #666; margin-bottom: 12px; flex-wrap: wrap; }}
        .card-actions {{ display: flex; gap: 8px; flex-wrap: wrap; }}
        .btn {{ padding: 7px 14px; border: none; border-radius: 5px; cursor: pointer; font-size: 12px; font-weight: bold; text-decoration: none; display: inline-block; }}
        .btn-view {{ background: #075e54; color: white; }}
        .btn-pause {{ background: #ff6b6b; color: white; }}
        .btn-resume {{ background: #51cf66; color: white; }}
        #notif {{ position: fixed; top: 15px; right: 15px; background: #333; color: white; padding: 10px 18px; border-radius: 8px; display: none; font-size: 13px; z-index: 999; }}
        .section-title {{ font-size: 14px; font-weight: bold; color: #666; margin-bottom: 10px; }}
    </style>
</head>
<body>
    <div class="header">
        <h2>🏢 Degenius Consult LTD — Admin Panel</h2>
        <p>Manage all WhatsApp AI conversations</p>
    </div>
    <div class="container">
        <div class="summary">
            <div class="summary-item">
                <div class="num">{len(leads)}</div>
                <div class="lbl">Total Leads</div>
            </div>
            <div class="summary-item">
                <div class="num">{len([l for l in leads if not l[2]])}</div>
                <div class="lbl">AI Active</div>
            </div>
            <div class="summary-item">
                <div class="num">{len([l for l in leads if l[2]])}</div>
                <div class="lbl">Paused</div>
            </div>
            <div class="summary-item">
                <div class="num">{len([l for l in leads if l[1] == 'lead_ready'])}</div>
                <div class="lbl">Ready to Process</div>
            </div>
        </div>
        <div class="section-title">RECENT CONVERSATIONS</div>
        {leads_html if leads_html else '<p style="color:#666;text-align:center;padding:20px">No conversations yet.</p>'}
    </div>
    <div id="notif"></div>
    <script>
        async function ctrl(cmd, userId) {{
            const r = await fetch('/control', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{command: cmd, user_id: userId, secret: '{CONTROL_SECRET}'}})
            }});
            const d = await r.json();
            const n = document.getElementById('notif');
            n.textContent = d.status || d.error;
            n.style.display = 'block';
            setTimeout(() => {{ n.style.display = 'none'; location.reload(); }}, 2500);
        }}
    </script>
</body>
</html>"""

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
