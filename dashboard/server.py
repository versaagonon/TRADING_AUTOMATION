import threading
import time
import os
import json
import importlib
import pandas as pd
import pandas_ta as ta
from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from report_generator import generate_pdf

app = Flask(__name__)
app.config['SECRET_KEY'] = 'malxgmn_secret_v100'
socketio = SocketIO(app, async_mode='threading', cors_allowed_origins="*", ping_timeout=10, ping_interval=5)

# CONFIG
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(os.path.abspath(os.path.join(BASE_DIR, "..")), "btc_2024_2025.json")

state = {
    "engine_running": False,
    "initial_balance": 100.0,
    "balance": 100.0,
    "position": None,
    "price": 0.0,
    "pnl": 0.0,
    "last_signal": "NONE",
    "true_signal": "WAITING",
    "signals_processed": 0,
    "correct_signals": 0,
    "ai_status": "WAITING...",
    "logs": ["[SYS] Protocol v10.0 (FUTURES) Online", "[SYS] Welcome Master Versaa!"],
    "sim_date": "-",
    "sim_index": 0,
    "strategy_name": "strategy1",
    "trade_history": []
}

df_historical = None
equity_history = []
trade_markers = []

def load_and_calculate_indicators(strategy_name):
    global df_historical
    if not os.path.exists(DATA_FILE): return False
    try:
        with open(DATA_FILE, 'r') as f: records = json.load(f)
        df = pd.DataFrame(records)
        df['close'] = df['close'].astype(float)
        
        spec = importlib.util.spec_from_file_location(strategy_name, os.path.join(BASE_DIR, "..", "strategy", f"{strategy_name}.py"))
        strat_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(strat_mod)
        df = strat_mod.calculate_indicators(df, ta)
        df_historical = df.dropna().reset_index(drop=True)
        return strat_mod
    except Exception as e: return None

def historical_sim_tracker(strategy_name):
    global df_historical, equity_history, trade_markers
    strat_mod = load_and_calculate_indicators(strategy_name)
    if not strat_mod: return
            
    total_records = len(df_historical)
    while not state["engine_running"]: time.sleep(1)
    
    for i in range(total_records - 5):
        if not state["engine_running"]: break
        try:
            row = df_historical.iloc[i]
            state["price"] = float(row['close'])
            state["sim_date"] = str(row['date'])
            
            # Ground truth
            next_price = float(df_historical.iloc[i+5]['close'])
            if next_price > state["price"] * 1.002: state["true_signal"] = "BUY"
            elif next_price < state["price"] * 0.998: state["true_signal"] = "SELL"
            else: state["true_signal"] = "HOLD"
            
            decision = strat_mod.get_signal(row, state["position"])
                    
            if decision != "HOLD":
                state["last_signal"] = decision
                state["signals_processed"] += 1
                
                # FUTURES LOGIC (LONG & SHORT)
                if decision == "BUY":
                    # 1. Jika ada SHORT, Tutup SHORT dulu
                    if state["position"] and state["position"]["type"] == "SHORT":
                        profit = (state["position"]["entry"] - state["price"]) * state["position"]["size"]
                        state["balance"] += profit
                        state["logs"].append(f"🔵 COVER SHORT @ {state['price']}. PNL: ${profit:.2f}")
                        state["trade_history"].append({"date": state["sim_date"], "type": "COVER", "price": state["price"], "balance": state["balance"], "result": "PROFIT" if profit > 0 else "LOSS"})
                        state["position"] = None
                    
                    # 2. Buka LONG jika kosong
                    if not state["position"]:
                        size = (state["balance"] * 0.5) / state["price"] 
                        state["position"] = {"type": "LONG", "entry": state["price"], "size": size}
                        state["logs"].append(f"🟢 OPEN LONG @ {state['price']}")
                        trade_markers.append({"time": i, "type": "BUY"})
                        state["trade_history"].append({"date": state["sim_date"], "type": "LONG", "price": state["price"], "balance": state["balance"], "result": "ENTRY"})

                elif decision == "SELL":
                    # 1. Jika ada LONG, Tutup LONG dulu
                    if state["position"] and state["position"]["type"] == "LONG":
                        profit = (state["price"] - state["position"]["entry"]) * state["position"]["size"]
                        state["balance"] += profit
                        state["logs"].append(f"🔴 CLOSE LONG @ {state['price']}. PNL: ${profit:.2f}")
                        state["trade_history"].append({"date": state["sim_date"], "type": "CLOSE", "price": state["price"], "balance": state["balance"], "result": "PROFIT" if profit > 0 else "LOSS"})
                        state["position"] = None
                    
                    # 2. Buka SHORT jika kosong
                    if not state["position"]:
                        size = (state["balance"] * 0.5) / state["price"] 
                        state["position"] = {"type": "SHORT", "entry": state["price"], "size": size}
                        state["logs"].append(f"🟠 OPEN SHORT @ {state['price']}")
                        trade_markers.append({"time": i, "type": "SELL"})
                        state["trade_history"].append({"date": state["sim_date"], "type": "SHORT", "price": state["price"], "balance": state["balance"], "result": "ENTRY"})
            
            # Kalkulasi PNL berjalan
            pnl_curr = 0.0
            if state["position"]:
                if state["position"]["type"] == "LONG":
                    pnl_curr = (state["price"] - state["position"]["entry"]) * state["position"]["size"]
                else: # SHORT
                    pnl_curr = (state["position"]["entry"] - state["price"]) * state["position"]["size"]
            
            equity = state["balance"] + pnl_curr
            state["pnl"] = equity - state["initial_balance"]
            equity_history.append(float(equity))
            
            # DINAMIS SPEED & EVENT THROTTLING (Anti-Crash)
            delay = 0.04
            emit_skip = 1
            
            if state.get("speed") == "fast": 
                delay = 0.01
                emit_skip = 3
            elif state.get("speed") == "super": 
                delay = 0      # No delay (True execution speed)
                emit_skip = 25 # Skip 25 frames per UI emit to prevent Browser OOM
            
            # Emit data hanya pada frame terpilih
            if i % emit_skip == 0:
                socketio.emit('raw_update', {
                    "price": state["price"], "pnl": state["pnl"], "balance": state["balance"], "equity": equity,
                    "current_idx": i, 
                    "equity_history": equity_history[-500:], "markers": trade_markers[-50:],
                    "true_signal": state["true_signal"], "sim_date": state["sim_date"], "logs": state["logs"][-30:],
                    "ai_status": state["ai_status"], "pos": state["position"],
                    "win_rate": (state["correct_signals"] / state["signals_processed"] * 100) if state["signals_processed"] > 0 else 0
                })
            
            if delay > 0:
                time.sleep(delay) 
        except Exception as e: print(f"Error: {e}")
    
    # SIMULATION FINISHED
    state["engine_running"] = False
    state["ai_status"] = "FINISHED (DATA END)"
    
    # AUTOMATIC AUDIT RECORD (Master Versaa Request)
    try:
        strategy = state.get("strategy_name", "Unknown")
        from report_generator import generate_csv_summary
        generate_csv_summary("history_trade.csv", state["initial_balance"], state["balance"], state["trade_history"], strategy_name=strategy)
        state["logs"].append(f"🟢 [AUDIT] Live History Updated: history_trade.csv")
    except Exception as e:
        print(f"Auto CSV Error: {e}")

    socketio.emit('raw_update', {"ai_status": state["ai_status"], "engine_running": False})

@app.route('/')
def index(): return render_template('index.html')

@app.route('/generate_report')
def report():
    try:
        filename = f"report_411_{int(time.time())}.pdf"
        strategy = state.get("strategy_name", "Unknown")
        generate_pdf(filename, state["initial_balance"], state["balance"], state["trade_history"], strategy_name=strategy)
        return jsonify({"status": "success", "filename": filename})
    except Exception as e: 
        print(f"PDF Error: {e}")
        return jsonify({"status": "error", "message": str(e)})

@socketio.on('start_engine')
def handle_start_engine(data):
    if not state["engine_running"]:
        # 1. HARD RESET ALL GLOBAL BUFFERS
        global equity_history, trade_markers
        equity_history = []
        trade_markers = []
        state["logs"] = ["[SYS] Resetting Engine Data...", "[SYS] Loading Strategy..."]
        state["trade_history"] = []
        state["position"] = None
        state["signals_processed"] = 0
        state["correct_signals"] = 0
        state["pnl"] = 0.0

        # 2. SYNC INITIAL STATE TO FRONTEND (CLEAN UI)
        state["initial_balance"] = data.get('initial_balance', 100.0)
        state["balance"] = state["initial_balance"]
        state["strategy_name"] = data.get('strategy', 'strategy1')
        state["speed"] = data.get('speed', 'normal') 
        state["engine_running"] = True
        state["ai_status"] = f"PREPARING ({state['strategy_name'].upper()})"
        
        # Kirim sinyal reset and state awal
        emit('raw_update', {"reset": True, "ai_status": state["ai_status"]})
        emit('state_update', state)
        
        # 3. START FRESH THREAD
        threading.Thread(target=historical_sim_tracker, args=(state["strategy_name"],), daemon=True).start()

@socketio.on('stop_engine')
def handle_stop_engine():
    state["engine_running"] = False
    state["ai_status"] = "FORCE STOPPED (USER)"
    # AUTOMATIC AUDIT RECORD ON FORCE STOP
    try:
        strategy = state.get("strategy_name", "Unknown")
        from report_generator import generate_csv_summary
        generate_csv_summary("history_trade.csv", state["initial_balance"], state["balance"], state["trade_history"], strategy_name=strategy)
    except Exception as e:
        print(f"Auto CSV Error: {e}")

    state["trade_history"] = [] # Reset after saving to PDF
    state["position"] = None
    state["pnl"] = 0.0
    state["balance"] = state["initial_balance"]
    emit('raw_update', {"ai_status": state["ai_status"], "engine_running": False, "reset": True})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
