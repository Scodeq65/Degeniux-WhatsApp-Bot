from flask import Flask, request
import requests
import json
from claude_agent import get_claude_response
import os

app = Flask(__name__)

WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN")

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
        print(f"WhatsApp API Status: {response.status_code}")
        print(f"WhatsApp API Response: {response.text}")
        return response
    except Exception as e:
        print(f"Error sending WhatsApp message: {e}")
        return None

@app.route("/", methods=["GET"])
def home():
    return "Degenius WhatsApp Bot is running!", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    
    print(f"Webhook verification attempt - Mode: {mode}, Token: {token}")
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    
    print("Webhook verification failed!")
    return "Forbidden", 403

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json()
    print(f"Incoming webhook data: {json.dumps(data, indent=2)}")
    
    try:
        entry = data["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]
        
        # Ignore status updates
        if "statuses" in value:
            return "OK", 200
        
        if "messages" in value:
            message = value["messages"][0]
            from_number = message["from"]
            message_type = message["type"]
            
            print(f"Message from: {from_number}, Type: {message_type}")
            
            # Handle text messages only
            if message_type == "text":
                user_message = message["text"]["body"]
                print(f"User message: {user_message}")
                
                # Get AI response
                ai_response = get_claude_response(from_number, user_message)
                print(f"AI response: {ai_response}")
                
                # Send response back
                send_whatsapp_message(from_number, ai_response)
            
            # Handle other message types gracefully
            elif message_type == "image":
                send_whatsapp_message(
                    from_number,
                    "Thanks for sending that! I can see you've shared an image. For registration purposes, kindly type out the details you need help with and I'll assist you right away. 😊"
                )
            
            elif message_type == "audio":
                send_whatsapp_message(
                    from_number,
                    "Hey! I noticed you sent a voice note. I work better with text messages — kindly type out what you need and I'll help you immediately. 😊"
                )
            
            elif message_type == "document":
                send_whatsapp_message(
                    from_number,
                    "Thanks for sending that document! Our team will review it shortly. In the meantime, is there anything else I can help you with?"
                )
            
            else:
                send_whatsapp_message(
                    from_number,
                    "Hey! Thanks for reaching out to Degenius Consult LTD. Kindly type your message and I'll be happy to assist you. 😊"
                )
    
    except KeyError as e:
        print(f"KeyError: {e} - Data structure might be different")
        print(f"Full data: {json.dumps(data, indent=2)}")
    
    except Exception as e:
        import traceback
        print(f"Unexpected error: {traceback.format_exc()}")
    
    return "OK", 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
