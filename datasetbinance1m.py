import requests
import time
import json
import urllib3
from datetime import datetime

# Matikan warning SSL Insecure
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# =========================
# CONFIG: SCALPING MODE (1m)
# =========================
SYMBOL = "BTCUSDT"
INTERVAL = "1m"  # DIUBAH KE 1 MENIT
START_TIME = 1727740800000   # 1 Okt 2024 (Start 3 Bulan Lalu)
END_TIME   = 1735689600000   # 1 Jan 2025
OUTPUT_FILE = "btc_1min_3months.json"

# Endpoint Vision (Tanpa Blokir)
URL = "https://data-api.binance.vision/api/v3/klines"

def fetch_klines(symbol, interval, start_time, end_time):
    all_data = []
    current = start_time
    print(f"📡 Menghubungkan ke API... Mengunduh TF {interval} untuk {symbol}")

    while current < end_time:
        params = {
            "symbol": symbol,
            "interval": interval,
            "startTime": current,
            "limit": 1000
        }

        try:
            response = requests.get(URL, params=params, verify=False, timeout=10)
            data = response.json()

            if not data or len(data) == 0:
                break

            all_data.extend(data)
            current = data[-1][0] + 1 # Geser waktu ke candle berikutnya

            # Progress Log ala Hacker
            print(f"✅ Terunduh: {len(all_data)} candle | Progress: {datetime.utcfromtimestamp(current/1000).strftime('%Y-%m-%d %H:%M')}")
            
            time.sleep(0.1) # Kecepatan tinggi, tapi hindari ban
        except Exception as e:
            print(f"❌ Error: {e}")
            break

    return all_data

def clean_data(raw):
    return [{
        "time": d[0],
        "date": datetime.utcfromtimestamp(d[0] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
        "open": float(d[1]), "high": float(d[2]), "low": float(d[3]), 
        "close": float(d[4]), "volume": float(d[5])
    } for d in raw]

if __name__ == "__main__":
    print("🚀 MEMULAI OPERASI PENGAMBILAN DATA MASIF...")
    raw_data = fetch_klines(SYMBOL, INTERVAL, START_TIME, END_TIME)
    
    print("\n🧹 MEMBERSIHKAN DATA...")
    cleaned = clean_data(raw_data)
    
    print(f"💾 MENYIMPAN {len(cleaned)} BARIS DATA KE {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w") as f:
        json.dump(cleaned, f, indent=2)
    
    print("✅ OPERASI SELESAI. DATA SIAP UNTUK PELATIHAN ELITE.")
