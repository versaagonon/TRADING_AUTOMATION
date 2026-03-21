import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  GEMINI PRO 1.5 — "QUANTUM TREND SURFER V13.0"
# ═══════════════════════════════════════════════════════════════════
#  Didekasikan khusus untuk Tuan Versaa.
#  Arsitektur ini dirombak total untuk mengalahkan CLAUDE OPUS (92.04%).
#
#  UPGRADE LOG V13.0:
#  ┌────────────────────────────────────────────────────────────────┐
#  │ #1  Multi-EMA Core (EMA 9, 21, 55, 200) + Acceleration Slope    │
#  │ #2  Stochastic RSI + MACD Aggressive Momentum                 │
#  │ #3  Keltner Channel Squeeze (Volatilitas ekstrim)              │
#  │ #4  Quantum 4-Level Trailing Stop (Hyper-Adaptive Profit Lock)│
#  │ #5  Smart Cooldown (Anti Dead-Cat Bounce)                     │
#  └────────────────────────────────────────────────────────────────┘
#
#  TARGET: ROI > 95% 
# ═══════════════════════════════════════════════════════════════════

# --- INTERNAL STATE TRACKER ---
_candles_in_pos = 0
_candles_since_exit = 99
_last_pos_type = "NONE"
_entry_price = 0.0
_max_favorable = 0.0

def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c = df['close']
    h = df['high']
    l = df['low']
    v = df['volume']

    # 1. LAYER TREN: Multi-EMA (Quantum Alignment)
    df['ema_9'] = c.ewm(span=9, adjust=False).mean()
    df['ema_21'] = c.ewm(span=21, adjust=False).mean()
    df['ema_55'] = c.ewm(span=55, adjust=False).mean()
    df['ema_200'] = c.ewm(span=200, adjust=False).mean()

    # Trend Acceleration Slope
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan) * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["trend_accel"] = df["ema9_slope"] - df["ema21_slope"]

    # 2. LAYER MOMENTUM: Stochastic RSI & MACD Aggressive
    # RSI 14
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(com=13, adjust=False).mean()
    loss = -delta.clip(upper=0).ewm(com=13, adjust=False).mean()
    rs = gain / loss.replace(0, np.nan)
    df['rsi_14'] = 100 - (100 / (1 + rs))

    # Stochastic RSI
    rsi_min = df['rsi_14'].rolling(14).min()
    rsi_max = df['rsi_14'].rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((df['rsi_14'] - rsi_min) / rsi_range) * 100
    df["stoch_rsi_k"] = stoch_k.rolling(3).mean()
    df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()

    # MACD 12/26/9
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # 3. LAYER VOLATILITY: Squeeze Detector (Bollinger + Keltner)
    # ATR 14
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df['atr'] = tr.ewm(com=13, adjust=False).mean()
    df['atr_pct'] = df['atr'] / c.replace(0, np.nan) * 100

    # Bollinger Band 20, 2.0
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # Keltner Channel 20, 1.5
    kc_mid = c.ewm(span=20, adjust=False).mean()
    df["kc_upper"] = kc_mid + 1.5 * df["atr"]
    df["kc_lower"] = kc_mid - 1.5 * df["atr"]

    # Squeeze Release: Saat BB keluar dari KC (ledakan volatilitas)
    df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
    df["squeeze_release"] = (~df["squeeze_on"]) & (df["squeeze_on"].shift(1).fillna(False))

    # 4. LAYER MARKET REGIME: ADX 
    up = h - h.shift(1)
    down = l.shift(1) - l
    pdm = np.where((up > down) & (up > 0), up, 0)
    mdm = np.where((down > up) & (down > 0), down, 0)
    
    atr_s = tr.ewm(com=13, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi = 100 * pd.Series(mdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    
    dx = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    df['adx_14'] = dx.ewm(com=13, adjust=False).mean()
    df['plus_di'] = pdi
    df['minus_di'] = mdi

    # 5. LAYER VOLUME
    df["vol_ma20"] = v.rolling(20).mean()
    df["vol_ratio"] = v / df["vol_ma20"].replace(0, np.nan)

    return df.fillna(0)


def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable

    # --- 1. Sinkronisasi State Tracker ---
    pos_type = position.get("type", "NONE") if position else "NONE"

    if pos_type != "NONE" and _last_pos_type != "NONE":
        _candles_in_pos += 1
    elif pos_type == "NONE" and _last_pos_type != "NONE":
        _candles_since_exit = 0
        _candles_in_pos = 0
        _entry_price = 0.0
        _max_favorable = 0.0
    elif pos_type == "NONE" and _last_pos_type == "NONE":
        _candles_since_exit = min(_candles_since_exit + 1, 99)
    elif pos_type != "NONE" and _last_pos_type == "NONE":
        _candles_in_pos = 1
        _entry_price = row["close"]
        _max_favorable = 0.0

    _last_pos_type = pos_type

    # --- 2. Ekstraksi Variabel ---
    price = row['close']
    ema9 = row['ema_9']
    ema21 = row['ema_21']
    ema55 = row['ema_55']
    ema200 = row['ema_200']
    ema21_slope = row['ema21_slope']
    trend_accel = row['trend_accel']
    
    rsi = row['rsi_14']
    stoch_k = row['stoch_rsi_k']
    stoch_d = row['stoch_rsi_d']
    macd = row['macd']
    macd_sig = row['macd_sig']
    macd_accel = row['macd_accel']
    
    atr_pct = row['atr_pct']
    bb_width = row['bb_width']
    squeeze_rel = row['squeeze_release']
    
    adx = row['adx_14']
    plus_di = row['plus_di']
    minus_di = row['minus_di']
    vol_ratio = row['vol_ratio']

    # Guard: Tunggu data memadai
    if ema200 == 0 or adx == 0:
        return "HOLD"

    # Anti-Sideways Filter
    if adx < 15 and bb_width < 0.01:
        return "HOLD"

    # ═══════════════════════════════════════════
    # 3. LOGIKA EXIT: QUANTUM 4-LEVEL TRAILING
    # ═══════════════════════════════════════════
    MIN_HOLD = 2  # Reaksi cepat Gemini Pro

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # Leveling Target ATR
        if _max_favorable > atr_pct * 3.0:
            trail_mult = 0.6  # Super Tight Lock (Level 4)
        elif _max_favorable > atr_pct * 2.0:
            trail_mult = 1.0  # Tight Lock (Level 3)
        elif _max_favorable > atr_pct * 1.0:
            trail_mult = 1.5  # Moderate (Level 2)
        else:
            trail_mult = 2.0  # Loose (Level 1)
            
        # Exit Condition 1: Trailing Stop Tersentuh
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.3

        # Exit Condition 2: Kerusakan Struktur Tren
        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (trend_accel < 0)

        # Exit Condition 3: RSI Overbought Extreme (Flash Exit)
        rsi_extreme = rsi > 82 + (adx / 10)  # RSI bisa tembus 85+ jika ADX sangat kuat (Dinamis)

        if trailing_hit or trend_broken or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # Leveling Target ATR
        if _max_favorable > atr_pct * 3.0:
            trail_mult = 0.6
        elif _max_favorable > atr_pct * 2.0:
            trail_mult = 1.0
        elif _max_favorable > atr_pct * 1.0:
            trail_mult = 1.5
        else:
            trail_mult = 2.0
            
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.3
        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (trend_accel > 0)
        rsi_extreme = rsi < 18 - (adx / 10)

        if trailing_hit or trend_broken or rsi_extreme:
            return "BUY"

    # ═══════════════════════════════════════════
    # 4. LOGIKA ENTRY: QUANTUM SCORING
    # ═══════════════════════════════════════════
    # Smart Cooldown
    COOLDOWN = 3
    if pos_type == "NONE" and _candles_since_exit < COOLDOWN:
        return "HOLD"

    if pos_type == "NONE":
        
        # --- Cek Peluang LONG ---
        long_score = 0
        if price > ema200 and ema21 > ema55: long_score += 1
        if macd > macd_sig and macd_accel > 0: long_score += 1
        if stoch_k > stoch_d and stoch_k < 75 and rsi > 45: long_score += 1
        if adx > 22 and plus_di > minus_di and ema21_slope > 0.03: long_score += 1
        if vol_ratio >= 1.2: long_score += 1
        if squeeze_rel and trend_accel > 0: long_score += 1  # Volatility breakout bonus
        
        # Mutlak: Momentum harus terarah naik dan di fase uptrend / early breakout
        if long_score >= 3:
            return "BUY"

        # --- Cek Peluang SHORT ---
        short_score = 0
        # BTC Bull Market Bias: Short butuh syarat extra (EMA55 < EMA200) agar tidak asal nge-short koreksi kecil
        if price < ema200 and ema21 < ema55 and ema55 < ema200: short_score += 1
        if macd < macd_sig and macd_accel < 0: short_score += 1
        if stoch_k < stoch_d and stoch_k > 25 and rsi < 55: short_score += 1
        if adx > 22 and minus_di > plus_di and ema21_slope < -0.03: short_score += 1
        if vol_ratio >= 1.2: short_score += 1
        if squeeze_rel and trend_accel < 0: short_score += 1

        # Short butuh konfirmasi kuat: 4 dari 6 Score
        if short_score >= 4:
            return "SELL"

    return "HOLD"