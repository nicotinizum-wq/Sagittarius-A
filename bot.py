import yfinance as yf
import pandas as pd
import requests

# ===== LINE設定 =====
LINE_TOKEN = "jMRMSpGfzt1lmcXlzr9JTAs577h5Z4YoV7VsHsBYMUxLrPAEDeQDJ6EEfDbQGEa0lrqcNm6Td5ouebumyzpjP2+iPTdeAiSu8e3O/M6sRlEoobG0amIbtDfiFlfTbx1kziTaZfkLXCglXkFTpqsP3QdB04t89/1O/w1cDnyilFU="

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = {
        "Authorization": f"Bearer {LINE_TOKEN}",
        "Content-Type": "application/json"
    }
    data = {
        "messages": [{"type": "text", "text": msg}]
    }
    requests.post(url, headers=headers, json=data)

# ===== 銘柄リスト（まずは堅実に）=====
stocks = [
    "7203.T", "6758.T", "9984.T", "8035.T", "6861.T",
    "9432.T", "8316.T", "6501.T", "6098.T", "4063.T",
    "6526.T", "4385.T", "3697.T", "3962.T", "6920.T"
]

results = []

# ===== スクリーニング =====
for ticker in stocks:
    try:
        data = yf.download(ticker, period="3mo", interval="1d")

        # データなし対策
        if data.empty or len(data) < 30:
            continue

        # 移動平均
        data["MA5"] = data["Close"].rolling(5).mean()
        data["MA25"] = data["Close"].rolling(25).mean()

        latest = data.iloc[-1]

        # 数値チェック（超重要）
        if pd.isna(latest["Close"]) or latest["Close"] <= 0:
            continue

        # 高値
        high_20 = data["High"].rolling(20).max().iloc[-1]

        # 条件
        if (
            latest["Close"] > 700 and
            latest["Close"] < 10000 and
            latest["MA5"] > latest["MA25"]
        ):
            score = (
                (latest["MA5"] - latest["MA25"]) / latest["MA25"] * 100 +
                (high_20 - latest["Close"]) / high_20 * 100
            )

            results.append((ticker, round(latest["Close"], 1), round(score, 2)))

    except:
        continue

# ===== 上位抽出 =====
results = sorted(results, key=lambda x: x[2], reverse=True)

# ===== LINE送信 =====
if results:
    message = "🔥 有望銘柄 TOP5\n\n"
    for r in results[:5]:
        message += f"{r[0]} 株価:{r[1]} スコア:{r[2]}\n"

    send_line(message)
    print(message)
else:
    send_line(" 条件に合う銘柄なし")
    print("なし")
