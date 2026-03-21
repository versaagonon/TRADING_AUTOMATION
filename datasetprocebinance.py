import requests
import time
import json
import urllib3
from datetime import datetime

# Matikan warning SSL Insecure
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================
# CONFIG
# =========================
SYMBOL = "BTCUSDT"
INTERVAL = "1h"
START_TIME = 1704067200000   # 1 Jan 2024
END_TIME   = 1735689600000   # 1 Jan 2025
OUTPUT_FILE = "btc_2024_2025.json"

# Gunakan endpoint vision yang tidak diblokir ISP
URL = "https://data-api.binance.vision/api/v3/klines"

# =========================
# FUNCTION FETCH DATA
# =========================
def fetch_klines(symbol, interval, start_time, end_time):
    all_data = []
    current = start_time

    while current < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current,
            "limit": 1000
        }

        response = requests.get(URL, params=params, verify=False, timeout=10)
        data = response.json()

        if not data:
            break

        all_data.extend(data)

        # next start
        current = data[-1][0] + 1

        print(f"Fetched: {len(all_data)} candles...")

        time.sleep(0.2)  # avoid rate limit

    return all_data

# =========================
# CLEAN DATA
# =========================
def clean_data(raw):
    clean = []

    for d in raw:
        clean.append({
            "time": d[0],
            "date": datetime.utcfromtimestamp(d[0] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
            "open": float(d[1]),
            "high": float(d[2]),
            "low": float(d[3]),
            "close": float(d[4]),
            "volume": float(d[5])
        })

    return clean

# =========================
# SAVE JSON
# =========================
def save_json(data, filename):
    with open(filename, "w") as f:
        json.dump(data, f, indent=2)
    print(f"Saved to {filename}")

# =========================
# MAIN
# =========================
if __name__ == "__main__":
    print("🚀 START DOWNLOAD...")

    raw_data = fetch_klines(SYMBOL, INTERVAL, START_TIME, END_TIME)

    print("🧹 CLEANING DATA...")
    cleaned = clean_data(raw_data)

    print("💾 SAVING JSON...")
    save_json(cleaned, OUTPUT_FILE)

    print("✅ DONE!")