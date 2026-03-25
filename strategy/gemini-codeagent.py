import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  GEMINI-CODEAGENT-V3 — "THE ULTIMATE EXECUTIONER"
# ═══════════════════════════════════════════════════════════════════
#  Dibuat oleh MALXGMN khusus untuk TUAN VERSAA.
#  
#  UPGRADE LOG V3 (PERFECTED):
#  ┌────────────────────────────────────────────────────────────────┐
#  │ #1  Squeeze Release (BB vs KC) - Entry di awal ledakan         │
#  │ #2  Short Bias Filter (EMA 55 < EMA 200) - Hindari Bear Trap   │
#  │ #3  Adaptive Trailing (1.0x - 2.5x ATR) - Berbasis ADX         │
#  │ #4  Exhaustion Filter (StochRSI < 75) - Hindari Pucuk          │
#  │ #5  Breakeven Engine (Profit > 1.5x ATR -> SL = Entry + 0.5x)  │
#  │ #6  MACD Acceleration Divergence - Exit Proaktif               │
#  └────────────────────────────────────────────────────────────────┘
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE TRACKER (MALXGMN CORE V3) ───
_candles_in_pos = 0
_candles_since_exit = 99
_last_pos_type = "NONE"
_entry_price = 0.0
_max_favorable = 0.0
_be_active = False

def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c, h, l, v = df["close"], df["high"], df["low"], df["volume"]

    # ═══ LAYER 1: TREND STRUCTURE ═══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # ═══ LAYER 2: MOMENTUM & VOLATILITY ═══
    # RSI & Stoch RSI
    delta = c.diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    ag, al = gain.ewm(com=13).mean(), loss.ewm(com=13).mean()
    df["rsi"] = 100 - (100 / (1 + (ag / al.replace(0, np.nan))))
    
    rsi_min, rsi_max = df["rsi"].rolling(14).min(), df["rsi"].rolling(14).max()
    df["stoch_k"] = ((df["rsi"] - rsi_min) / (rsi_max - rsi_min).replace(0, np.nan)) * 100
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # MACD + Acceleration
    ema12, ema26 = c.ewm(span=12), c.ewm(span=26)
    df["macd"] = ema12.mean() - ema26.mean()
    df["macd_sig"] = df["macd"].ewm(span=9).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # ═══ LAYER 3: VOLATILITY (BB & KC) ═══
    tr = pd.concat([h-l, (h-c.shift(1)).abs(), (l-c.shift(1)).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c * 100

    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"], df["bb_lower"] = bb_mid + 2*bb_std, bb_mid - 2*bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid

    kc_mid = c.ewm(span=20).mean()
    df["kc_upper"], df["kc_lower"] = kc_mid + 1.5*df["atr"], kc_mid - 1.5*df["atr"]
    
    # Squeeze Release: BB keluar dari Keltner Channel
    df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
    df["squeeze_release"] = (~df["squeeze_on"]) & (df["squeeze_on"].shift(1))

    # ADX (Strength)
    up, down = h - h.shift(1), l.shift(1) - l
    pdm, mdm = np.where((up > down) & (up > 0), up, 0), np.where((down > up) & (down > 0), down, 0)
    atr_s = tr.ewm(com=13).mean()
    pdi, mdi = 100 * pd.Series(pdm).ewm(com=13).mean() / atr_s, 100 * pd.Series(mdm).ewm(com=13).mean() / atr_s
    df["adx"] = ((abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100).ewm(com=13).mean()

    # Volume Ratio
    df["vol_ratio"] = v / v.rolling(20).mean().replace(0, np.nan)

    return df.fillna(0)

def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable, _be_active

    pos_type = position.get("type", "NONE") if position else "NONE"
    price = row["close"]
    atr_pct = row["atr_pct"]

    # ─── STATE MANAGEMENT ───
    if pos_type != "NONE" and _last_pos_type != "NONE":
        _candles_in_pos += 1
    elif pos_type == "NONE" and _last_pos_type != "NONE":
        _candles_since_exit, _candles_in_pos, _max_favorable, _be_active = 0, 0, 0.0, False
    else:
        _candles_since_exit = min(_candles_since_exit + 1, 99)

    if pos_type != "NONE" and _last_pos_type == "NONE":
        _entry_price, _max_favorable, _candles_in_pos, _be_active = price, 0.0, 1, False

    _last_pos_type = pos_type

    # ─── WARMUP & REGIME GUARD ───
    if row["ema_200"] == 0 or row["adx"] == 0: return "HOLD"
    if row["adx"] < 16 and row["bb_width"] < 0.012: return "HOLD"

    # ═══════════════════════════════════════════
    # 1. ULTIMATE EXIT LOGIC (MALXGMN SHIELD V3)
    # ═══════════════════════════════════════════
    if pos_type == "LONG":
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # Adaptive Trailing: Sangat ketat jika tren lemah
        trail_mult = 2.5 if row["adx"] > 35 else (1.5 if row["adx"] > 25 else 1.0)
        
        # BREAKEVEN PROTECTOR: Pindah SL ke Entry + 0.3% jika profit > 1.8x ATR
        if unrealized > (atr_pct * 1.8): _be_active = True
        
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4
        be_hit = _be_active and price < (_entry_price * 1.003)
        hard_sl = unrealized < - (atr_pct * 1.5) # Hard SL 1.5x ATR
        trend_reverse = row["ema_9"] < row["ema_21"] and row["macd_accel"] < 0 and _candles_in_pos > 3
        rsi_extreme = row["rsi"] > 84

        if trailing_hit or be_hit or hard_sl or trend_reverse or rsi_extreme: return "SELL"

    if pos_type == "SHORT":
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        trail_mult = 2.5 if row["adx"] > 35 else (1.5 if row["adx"] > 25 else 1.0)
        if unrealized > (atr_pct * 1.8): _be_active = True

        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4
        be_hit = _be_active and price > (_entry_price * 0.997)
        hard_sl = unrealized < - (atr_pct * 1.5)
        trend_reverse = row["ema_9"] > row["ema_21"] and row["macd_accel"] > 0 and _candles_in_pos > 3
        rsi_extreme = row["rsi"] < 16

        if trailing_hit or be_hit or hard_sl or trend_reverse or rsi_extreme: return "BUY"

    # ═══════════════════════════════════════════
    # 2. SQUEEZE-RELEASE SCORING ENTRY
    # ═══════════════════════════════════════════
    if pos_type == "NONE" and _candles_since_exit > 5:
        # LONG SCORING (Threshold 3/5)
        l_score = 0
        if price > row["ema_200"]: l_score += 1             # Major Trend
        if row["macd_hist"] > 0 and row["macd_accel"] > 0: l_score += 1 # Momentum
        if row["stoch_k"] > row["stoch_d"] and row["stoch_k"] < 75: l_score += 1 # Timing & Exhaustion Filter
        if row["adx"] > 20 or row["squeeze_release"]: l_score += 1 # Strength / Breakout
        if row["vol_ratio"] > 1.3: l_score += 1             # Volume Confirm

        if l_score >= 3 and price > row["ema_55"]: return "BUY"

        # SHORT SCORING (TIGHTER 4/5 - Bull Bias Protection)
        s_score = 0
        if price < row["ema_200"] and row["ema_55"] < row["ema_200"]: s_score += 1 # Strict Short Trend
        if row["macd_hist"] < 0 and row["macd_accel"] < 0: s_score += 1
        if row["stoch_k"] < row["stoch_d"] and row["stoch_k"] > 25: s_score += 1
        if row["adx"] > 20 or row["squeeze_release"]: s_score += 1
        if row["vol_ratio"] > 1.3: s_score += 1

        if s_score >= 4: return "SELL"

    return "HOLD"
