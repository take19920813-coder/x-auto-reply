import os
import time
import requests

X_BEARER_TOKEN = os.environ["X_BEARER_TOKEN"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STREAM_URL = (
    "https://api.x.com/2/tweets/search/stream"
    "?tweet.fields=created_at,author_id"
)

x_headers = {
    "Authorization": f"Bearer {X_BEARER_TOKEN}"
}

def send_telegram(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text
        },
        timeout=20
    )
    response.raise_for_status()

def run_stream():
    with requests.get(
        STREAM_URL,
        headers=x_headers,
        stream=True,
        timeout=90
    ) as response:

        response.raise_for_status()

        send_telegram("✅ X監視を開始しました")

        for line in response.iter_lines():
            if not line:
                continue



            import json
            item = json.loads(line.decode("utf-8"))

            data = item.get("data")
            if not data:
                continue

            post_id = data.get("id")
            text = data.get("text", "")

            message = (
                "🚨 X新規投稿\n\n"
                f"{text}\n\n"
                f"https://x.com/i/web/status/{post_id}"
            )

            send_telegram(message)

while True:
    try:
        run_stream()
    except Exception as e:
        print("Stream error:", repr(e), flush=True)
        time.sleep(10)
