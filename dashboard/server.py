import threading
import time
import os
import json
import pandas as pd
import pandas_ta as ta
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'malxgmn_secret_v80'
# Kurangi ping_timeout agar lebih responsif
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*", ping_timeout=10, ping_interval=5)

# CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(os.path.abspath(os.path.join(BASE_DIR, "..")), "btc_2024_2025.json")

state = {
    "engine_running": False,
    "balance": 10000.0,
    "position": None,
    "price": 0.0,
    "pnl": 0.0,
    "last_signal": "NONE",
    "true_signal": "WAITING",
    "signals_processed": 0,
    "correct_signals": 0,
    "ai_status": "WAITING...",
    "logs": ["[SYS] Protocol v8.0 (ULTRA-SYNC) Online", "[SYS] Waiting for Launch Sequence..."],
    "sim_date": "-",
    "sim_index": 0,
}

df_historical = None
equity_history = []
trade_markers = []

def load_and_calculate_indicators():
    global df_historical
    print("[*] Loading DATA & Calculating Indicators...")
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r') as f:
            records = json.load(f)
        df = pd.DataFrame(records)
        df['close'] = df['close'].astype(float)
        df['volume'] = df['volume'].astype(float)
        
        # Indikator teknikal untuk strategi agresif
        df['EMA_12'] = ta.ema(df['close'], length=12)
        df['EMA_26'] = ta.ema(df['close'], length=26)
        df['RSI_9'] = ta.rsi(df['close'], length=9) # RSI lebih pendek agar lebih sensitif
        df['VOL_SMA_20'] = ta.sma(df['volume'], length=20)
        
        df_historical = df.dropna().reset_index(drop=True)
        print(f"[✔] Successfully processed {len(df_historical)} valid records.")
        return True
    except Exception as e:
        print(f"Error initializing data: {e}")
        return False

# ==========================================
# SIMULATION ENGINE 
# ==========================================
def historical_sim_tracker():
    global df_historical, equity_history, trade_markers
    print("[*] Simulation Thread Starting...")
    
    if df_historical is None:
        if not load_and_calculate_indicators(): return
            
    total_records = len(df_historical)
    while not state["engine_running"]: time.sleep(1)
        
    print("[+] Engine Starting Sync...")
    state["logs"].append("[SYS] ENGINE STARTED. Ultra-Sync Data Streaming...")
    state["ai_status"] = "ACTIVE (v8.0 SYNC)"
    
    for i in range(total_records - 5):
        if not state["engine_running"]: break
            
        try:
            row = df_historical.iloc[i]
            state["price"] = float(row['close'])
            state["sim_date"] = str(row['date'])
            state["sim_index"] = i
            
            # Ground truth (5 candle ke depan)
            next_price = float(df_historical.iloc[i+5]['close'])
            if next_price > state["price"] * 1.002: state["true_signal"] = "BUY"
            elif next_price < state["price"] * 0.998: state["true_signal"] = "SELL"
            else: state["true_signal"] = "HOLD"
            
            ema12 = row['EMA_12']
            ema26 = row['EMA_26']
            rsi = row['RSI_9']
            
            decision = "HOLD"
            # STRATEGI AGRESIF V8.0
            if not state["position"]:
                # EMA Crossover + Momentum RSI
                if (ema12 > ema26) and (rsi > 50): decision = "BUY"
            else:
                # EMA Cross Down atau RSI Overbought
                if (ema12 < ema26) or (rsi > 80): decision = "SELL"
                    
            if decision != "HOLD":
                state["last_signal"] = decision
                state["signals_processed"] += 1
                if decision == state["true_signal"]:
                    state["correct_signals"] += 1
                    
                if decision == "BUY" and not state["position"]:
                    size = (state["balance"] * 0.5) / state["price"] 
                    state["position"] = {"type": "BUY", "entry": state["price"], "size": size}
                    state["logs"].append(f"🟢 BUY @ {state['price']}")
                    trade_markers.append({"time": i, "type": "BUY"})
                    
                elif decision == "SELL" and state["position"]:
                    profit = (state["price"] - state["position"]["entry"]) * state["position"]["size"]
                    state["balance"] += profit
                    state["position"] = None
                    state["logs"].append(f"🔴 SELL @ {state['price']}. PNL: ${profit:.2f}")
                    trade_markers.append({"time": i, "type": "SELL"})
            
            # HITUNG EKUITAS & PNL
            pnl_current = (state["price"] - state["position"]["entry"]) * state["position"]["size"] if state["position"] else 0.0
            equity = state["balance"] + pnl_current
            state["pnl"] = equity - 10000.0
            equity_history.append(float(equity))
            
            # ULTRA-SYNC EMIT (Satu Emit untuk SEMUA Data)
            # Ini menjamin Log and Ground Truth sinkron 100%
            socketio.emit('raw_update', {
                "price": state["price"], 
                "pnl": state["pnl"], 
                "balance": state["balance"],
                "equity": equity,
                "equity_history": equity_history[-500:], 
                "markers": trade_markers[-50:],
                "true_signal": state["true_signal"],
                "sim_date": state["sim_date"],
                "logs": state["logs"][-30:], # Kirim logs terbaru setiap detak!
                "ai_status": state["ai_status"],
                "pos": state["position"],
                "win_rate": (state["correct_signals"] / state["signals_processed"] * 100) if state["signals_processed"] > 0 else 0
            })

            time.sleep(0.04) 
        except Exception as e:
            print(f"Error Loop: {e}")

# ==========================================
# BOOT
# ==========================================
@app.route('/')
def index(): return render_template('index.html')

@socketio.on('connect')
def browser_connect():
    print("[+] Browser Connected")
    emit('state_update', state)

@socketio.on('start_engine')
def handle_start_engine(data):
    if not state["engine_running"]:
        state["engine_running"] = True
        state["logs"].append("[SYS] Engine Activated...")
        emit('state_update', state)
        
if __name__ == '__main__':
    print("\n" + "="*50)
    print(" [✔] 411 NATIVE SYNC CORE v8.0 ")
    print("="*50 + "\n")
    load_and_calculate_indicators()
    threading.Thread(target=historical_sim_tracker, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
