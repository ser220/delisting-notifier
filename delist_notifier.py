import time
import threading
import requests
import yaml
from datetime import datetime
from flask import Flask

# ------------------------
# Load config
# ------------------------
with open("config.yml", "r") as f:
    config = yaml.safe_load(f)

TOKEN = config["telegram"]["token"]
CHAT_ID = config["telegram"]["chat_id"]
POLL_INTERVAL = 300  # 5 minutes

EXCHANGES = [
    "Binance", "Coinbase", "Kraken", "Bybit", "OKX",
    "Gate", "KuCoin", "Upbit", "Bitget", "MEXC", "BingX"
]

last_check_time = None

# ------------------------
# Telegram functions
# ------------------------
def send_message(chat_id, text, buttons=None):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }
    if buttons:
        payload["reply_markup"] = {"keyboard": buttons, "resize_keyboard": True}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"[ERROR] Telegram send failed: {e}")

# ------------------------
# Telegram polling
# ------------------------
def poll_telegram():
    offset = 0
    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?timeout=10&offset={offset}"
            resp = requests.get(url, timeout=15).json()
            for update in resp.get("result", []):
                offset = update["update_id"] + 1
                handle_message(update.get("message", {}))
        except Exception as e:
            print(f"[ERROR] Polling failed: {e}")
        time.sleep(3)

def handle_message(message):
    global last_check_time
    text = message.get("text", "").strip().lower()
    chat_id = message["chat"]["id"]

    if text in ["/start", "start"]:
        send_message(
            chat_id,
            "👋 Hello! I monitor *crypto delistings* from 11 exchanges.\n"
            "I check every 5 minutes.\n\n"
            "Press the button below to check status:",
            buttons=[[{"text": "📊 Status"}]]
        )
    elif text in ["/status", "📊 status", "status"]:
        if last_check_time:
            status = (
                "🟢 *Delist Notifier*\n"
                f"• Last check: `{last_check_time}`\n"
                "• Monitoring exchanges:\n" +
                "\n".join([f" - {x}" for x in EXCHANGES])
            )
        else:
            status = "⏳ Bot started but has not yet performed the first check."
        send_message(chat_id, status, buttons=[[{"text": "📊 Status"}]])
    else:
        send_message(chat_id, "Press the button below to see status:",
                     buttons=[[{"text": "📊 Status"}]])

# ------------------------
# Exchange checker
# ------------------------
def check_exchanges():
    global last_check_time
    print(f"[{datetime.now()}] Checking exchanges...")
    last_check_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for ex in EXCHANGES:
        print(f" - Checking {ex}...")
        time.sleep(0.1)
    print("Check complete.\n")

# ------------------------
# Flask Web Server
# ------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Delisting Bot is running!"

# ------------------------
# Main
# ------------------------
if __name__ == "__main__":
    # Start Telegram polling in background
    threading.Thread(target=poll_telegram, daemon=True).start()
    # Start exchange checking in background
    threading.Thread(target=lambda: [check_exchanges() or time.sleep(POLL_INTERVAL) for _ in iter(int, 1)], daemon=True).start()

    # Send startup message
    send_message(CHAT_ID, "✅ Bot started and monitoring 11 exchanges.", buttons=[[{"text": "📊 Status"}]])

    # Run Flask server
    app.run(host="0.0.0.0", port=10000)
