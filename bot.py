import yfinance as yf
import pandas as pd
from concurrent.futures import ThreadPoolExecutor
import requests

# =========================
# LINE設定
# =========================
LINE_TOKEN = "jMRMSpGfzt1lmcXlzr9JTAs577h5Z4YoV7VsHsBYMUxLrPAEDeQDJ6EEfDbQGEa0lrqcNm6Td5ouebumyzpjP2+iPTdeAiSu8e3O/M6sRlEoobG0amIbtDfiFlfTbx1kziTaZfkLXCglXkFTpqsP3QdB04t89/1O/w1cDnyilFU="

def send_line(msg):
    url = "https://api.line.me/v2/bot/message/broadcast"
    headers = { "Authorization": f"Bearer {LINE_TOKEN}", "Content-Type": "application/json" }
    data = { "messages": [{"type": "text", "text": msg}] }
    requests.post(url, headers=headers, json=data)

# =========================
# 銘柄リスト
# =========================
stocks = [f"{i}.T" for i in range(1300, 7000)]

results = []

# =========================
# 地合いチェック
# =========================
nikkei = yf.download("^N225", period="3mo", interval="1d", auto_adjust=True, progress=False)

if not nikkei.empty and len(nikkei) >= 25:
    nikkei_close = nikkei["Close"]
    if isinstance(nikkei_close, pd.DataFrame):
        nikkei_close = nikkei_close.iloc[:, 0]

    nikkei_ma25 = float(nikkei_close.rolling(25).mean().iloc[-1])
    nikkei_now = float(nikkei_close.iloc[-1])

    if nikkei_now < nikkei_ma25:
        print("⚠️ 地合い弱い → 見送り推奨")

# =========================
# スクリーニング関数
# =========================
def check_stock(ticker):
    try:
        data = yf.download(ticker, period="3mo", interval="1d", auto_adjust=True, progress=False)

        if data.empty or len(data) < 25:
            return None

        close_series = data["Close"]
        if isinstance(close_series, pd.DataFrame):
            close_series = close_series.iloc[:, 0]

        data["MA5"] = close_series.rolling(5).mean()
        data["MA25"] = close_series.rolling(25).mean()

        latest = data.iloc[-1]

        close = float(close_series.iloc[-1])
        ma5 = float(data["MA5"].iloc[-1])
        ma25 = float(data["MA25"].iloc[-1])
        volume = float(data["Volume"].iloc[-1])

        high_20 = float(data["High"].rolling(20).max().iloc[-1])
        volume_avg = float(data["Volume"].rolling(5).mean().iloc[-1])

        if (
            close > 700 and close < 10000 and
            ma5 > ma25 and
            (high_20 - close) / high_20 > 0.03 and
            volume > volume_avg
        ):
            score = ((ma5 - ma25) / ma25) + (volume / volume_avg)
            return (ticker, round(close,1), round(score,2))
        else:
            return None
    except:
        return None

# =========================
# 並列処理
# =========================
with ThreadPoolExecutor(max_workers=10) as executor:
    for res in executor.map(check_stock, stocks):
        if res:
            results.append(res)

# =========================
# ランキング
# =========================
results = sorted(results, key=lambda x: x[2], reverse=True)

print("🔥 有望銘柄 TOP10")
for r in results[:10]:
    print(r)

# =========================
# バックテスト
# =========================
def backtest(ticker):
    data = yf.download(ticker, period="6mo", interval="1d", auto_adjust=True, progress=False)

    if data.empty or len(data) < 30:
        return None

    close_series = data["Close"]
    if isinstance(close_series, pd.DataFrame):
        close_series = close_series.iloc[:, 0]

    data["MA5"] = close_series.rolling(5).mean()
    data["MA25"] = close_series.rolling(25).mean()

    wins = 0
    losses = 0

    for i in range(25, len(data)-5):
        close = float(close_series.iloc[i])
        ma5 = float(data["MA5"].iloc[i])
        ma25 = float(data["MA25"].iloc[i])

        if ma5 > ma25:
            buy_price = close
            future = data.iloc[i+1:i+6]

            hit = False
            for _, f in future.iterrows():
                high = float(f["High"])
                low = float(f["Low"])

                if high >= buy_price * 1.05:
                    wins += 1
                    hit = True
                    break
                if low <= buy_price * 0.98:
                    losses += 1
                    hit = True
                    break

            if not hit:
                losses += 1

    total = wins + losses
    if total == 0:
        return None

    win_rate = wins / total
    return round(win_rate,2), total

print("\n📊 簡易バックテスト（上位5銘柄）")
for r in results[:5]:
    bt = backtest(r[0])
    if bt:
        print(r[0], "勝率:", bt[0], "試行回数:", bt[1])

# =========================
# LINE通知
# =========================
message = "🔥有望銘柄TOP3\n"

for r in results[:3]:
    message += f"{r[0]} 株価:{r[1]} スコア:{r[2]}\n"

send_line(message)

