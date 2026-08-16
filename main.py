import os
import json
import time
import re
import requests

X_BEARER_TOKEN = os.environ["X_BEARER_TOKEN"]
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STREAM_URL = (
    "https://api.x.com/2/tweets/search/stream"
    "?tweet.fields=created_at,author_id"
    "&expansions=author_id"
    "&user.fields=username,name"
)

X_HEADERS = {
    "Authorization": f"Bearer {X_BEARER_TOKEN}"
}

# 強材料
VERY_STRONG = [
    "買収", "TOB", "MBO", "公開買付",
    "大量保有", "大量保有報告書",
    "投資開始", "株を買った", "株式を購入",
    "保有しました", "取得しました",
    "資本業務提携", "業務提携",
    "自社株買い", "自己株式取得",
    "上方修正", "増配", "特別配当",
    "承認取得", "承認され", "認可",
    "大型受注", "大口受注",
    "独占契約", "大型契約"
]

# 通常材料
STRONG = [
    "投資", "購入", "保有", "株主",
    "決算", "業績", "売上", "利益",
    "提携", "契約", "受注",
    "新製品", "新サービス",
    "特許", "承認", "治験",
    "増資", "減資",
    "増配", "減配",
    "株主優待",
    "ストップ高", "ストップ安",
    "上場", "東証", "グロース", "プライム", "スタンダード",
    "時価総額"
]

# ネガティブ材料も通知
NEGATIVE = [
    "下方修正", "赤字", "減損",
    "不祥事", "粉飾", "行政処分",
    "訴訟", "リコール",
    "上場廃止", "監理銘柄",
    "減配", "無配"
]

# 株に関係なさそうな投稿を落とす
NOISE = [
    "おはよう", "おやすみ",
    "ランチ", "ご飯", "旅行",
    "介護", "ゲーム", "映画",
    "天気", "暑い", "寒い"
]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    r = requests.post(
        url,
        data={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True
        },
        timeout=20
    )
    r.raise_for_status()

def score_post(text):
    score = 0
    reasons = []

    lower = text.lower()

    for word in VERY_STRONG:
        if word.lower() in lower:
            score += 5
            reasons.append(word)

    for word in STRONG:
        if word.lower() in lower:
            score += 2
            reasons.append(word)

    for word in NEGATIVE:
        if word.lower() in lower:
            score += 4
            reasons.append(word)

    # 日本株の4桁証券コード
    if re.search(r'(?<!\d)\d{4}(?!\d)', text):
        score += 3
        reasons.append("4桁コード")

    # 株式用語
    if any(x in text for x in [
        "銘柄", "株価", "株式", "証券コード",
        "東証", "上場企業"
    ]):
        score += 2
        reasons.append("株式関連")

    # $3895 のようなcashtag
    if re.search(r'\$\d{4}', text):
        score += 4
        reasons.append("cashtag")

    # 雑談だけなら減点
    if not reasons:
        for word in NOISE:
            if word in text:
                score -= 5

    return score, list(dict.fromkeys(reasons))

def run_stream():
    with requests.get(
        STREAM_URL,
        headers=X_HEADERS,
        stream=True,
        timeout=90
    ) as response:

        response.raise_for_status()

        print("X stream connected", flush=True)

        for line in response.iter_lines():
            if not line:
                continue

            try:
                item = json.loads(line.decode("utf-8"))
            except Exception:
                continue

            data = item.get("data")
            if not data:
                continue

            post_id = data.get("id")
            text = data.get("text", "")

            users = item.get("includes", {}).get("users", [])
            username = users[0].get("username", "unknown") if users else "unknown"

            # RTは通知しない
            if text.startswith("RT @"):
                continue

            score, reasons = score_post(text)

            # ここが通知基準
            if score < 5:
                continue

            if score >= 10:
                level = "🔥 S"
            elif score >= 7:
                level = "🚨 A"
            else:
                level = "⚠️ B"

            reason_text = " / ".join(reasons[:6])

            message = (
                f"{level} 株価材料候補\n\n"
                f"投稿者: @{username}\n"
                f"判定材料: {reason_text}\n"
                f"スコア: {score}\n\n"
                f"{text}\n\n"
                f"https://x.com/{username}/status/{post_id}"
            )

            send_telegram(message)

while True:
    try:
        run_stream()

    except requests.exceptions.HTTPError as e:
        print("HTTP error:", repr(e), flush=True)
        time.sleep(30)

    except requests.exceptions.RequestException as e:
        print("Connection error:", repr(e), flush=True)
        time.sleep(10)

    except Exception as e:
        print("Unexpected error:", repr(e), flush=True)
        time.sleep(10)
