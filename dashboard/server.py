import threading
import time
import os
import json
import pandas as pd
import pandas_ta as ta
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'malxgmn_secret_v50'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*")

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
    "logs": ["[SYS] Protocol v5.0 (NATIVE DATA ENGINE) Online", "[SYS] Waiting for Launch Sequence..."],
    "sim_date": "-",
    "sim_index": 0,
}

df_historical = None
equity_history = []
trade_markers = [] # [{time: x, type: 'BUY/SELL', price: y}]

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
        
        df['EMA_50'] = ta.ema(df['close'], length=50)
        df['EMA_200'] = ta.ema(df['close'], length=200)
        df['RSI_14'] = ta.rsi(df['close'], length=14)
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
        
    print("[+] Engine Starting...")
    state["logs"].append("[SYS] ENGINE STARTED. Flowing Native Data...")
    state["ai_status"] = "ACTIVE (NATIVE)"
    socketio.emit('state_update', state)
    
    for i in range(total_records - 5):
        if not state["engine_running"]: break
            
        try:
            row = df_historical.iloc[i]
            state["price"] = float(row['close'])
            state["sim_date"] = str(row['date'])
            state["sim_index"] = i
            
            # Ground truth
            next_price = float(df_historical.iloc[i+5]['close'])
            if next_price > state["price"] * 1.005: state["true_signal"] = "BUY"
            elif next_price < state["price"] * 0.995: state["true_signal"] = "SELL"
            else: state["true_signal"] = "HOLD"
            
            ema50 = row['EMA_50']
            ema200 = row['EMA_200']
            rsi = row['RSI_14']
            vol = row['volume']
            vol_sma = row['VOL_SMA_20']
            
            decision = "HOLD"
            if not state["position"]:
                if (state["price"] > ema200) and (ema50 > ema200) and (rsi < 40) and (vol > vol_sma): decision = "BUY"
            else:
                if (state["price"] < ema50) or (rsi > 70): decision = "SELL"
                    
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
            
            pnl = (state["price"] - state["position"]["entry"]) * state["position"]["size"] if state["position"] else 0.0
            state["pnl"] = pnl
            equity = state["balance"] + pnl
            equity_history.append(float(equity))
            
            # Kirim Data Mentah Berkecepatan Tinggi
            socketio.emit('raw_update', {
                "price": state["price"], 
                "pnl": state["pnl"], 
                "balance": state["balance"],
                "equity": equity,
                "equity_history": equity_history[-500:], # Batasi 500 data terakhir
                "markers": trade_markers[-50:],
                "true_signal": state["true_signal"],
                "sim_date": state["sim_date"]
            })

            if i % 10 == 0: socketio.emit('state_update', state)
            time.sleep(0.005) # SPEED HACK: Sangat Cepat
        except Exception as e:
            print(f"Error in Loop: {e}")

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
    print(" [✔] 411 NATIVE DATA CORE v5.0 ")
    print("="*50 + "\n")
    load_and_calculate_indicators()
    threading.Thread(target=historical_sim_tracker, daemon=True).start()
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
