import pandas as pd
import pandas_ta as ta
import numpy as np

def calculate_indicators(df, ta):
    df = df.copy()
    c = df["close"]; h = df["high"]; l = df["low"]; v = df["volume"]

    # ══ LAYER TRENDS: EMA & Slope ══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()
    # Perbedaan kemiringan EMA untuk deteksi percepatan tren
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan) * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["trend_accel"] = df["ema9_slope"] - df["ema21_slope"]  # Positif = tren menguat

    # ══ LAYER MOMENTUM: RSI, Stochastic RSI, MACD ══
    # RSI klasik (14)
    delta = c.diff(); gain = delta.clip(lower=0); loss = -delta.clip(upper=0)
    ag = gain.ewm(com=13, adjust=False).mean(); al = loss.ewm(com=13, adjust=False).mean()
    rs = ag / al.replace(0, np.nan); df["rsi"] = 100 - (100 / (1 + rs))
    # Stochastic RSI (timing entry lebih presisi)
    rsi_series = df["rsi"]
    rsi_min = rsi_series.rolling(14).min(); rsi_max = rsi_series.rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((rsi_series - rsi_min) / rsi_range) * 100
    df["stoch_rsi_k"] = stoch_k.rolling(3).mean()
    df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()
    # MACD (12,26,9) dan momentum-nya
    ema12 = c.ewm(span=12, adjust=False).mean(); ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)  # Percepatan momentum

    # ══ LAYER VOLATILITY: ATR & Bollinger ══
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100
    # Bollinger Bands (20,2) & lebar pita (squeeze detection)
    bb_mid = c.rolling(20).mean(); bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # ══ LAYER TREN STRENGTH: ADX ══
    up = h - h.shift(1); down = l.shift(1) - l
    pdm = np.where((up > down) & (up>0), up, 0); mdm = np.where((down > up) & (down>0), down, 0)
    atr_s = tr.ewm(com=13, adjust=False).mean()
    pdi = 100 * pd.Series(pdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi = 100 * pd.Series(mdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx  = (abs(pdi - mdi) / (pdi + mdi).replace(0,np.nan)) * 100
    df["adx"]      = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]  = pdi; df["minus_di"] = mdi

    # ══ LAYER VOLUME: Konfirmasi volume ══
    df["vol_ma20"]  = v.rolling(20).mean()
    df["vol_ratio"] = v / df["vol_ma20"].replace(0, np.nan)
    df["vol_rising"] = (v > v.shift(1)) & (v.shift(1) > v.shift(2))

    return df.replace([np.inf, -np.inf], np.nan).fillna(0)
# ─── INTERNAL STATE TRACKER ───
_candles_in_pos     = 0
_candles_since_exit = 99
_last_pos_type      = "NONE"
_entry_price        = 0.0
_max_favorable      = 0.0

def get_signal(row, position):
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable

    # ── 1. State Parsing ──
    pos_type = position.get("type", "NONE") if position else "NONE"

    # ── 2. Internal State Machine ──
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

    # ── 3. Ekstrak variabel penting ──
    price       = row["close"]
    ema9        = row["ema_9"]
    ema21       = row["ema_21"]
    ema55       = row["ema_55"]
    ema200      = row["ema_200"]
    ema21_slope = row["ema21_slope"]
    rsi         = row["rsi"]
    stoch_k     = row["stoch_rsi_k"]
    stoch_d     = row["stoch_rsi_d"]
    macd        = row["macd"]
    macd_sig    = row["macd_sig"]
    macd_accel  = row["macd_accel"]
    atr_pct     = row["atr_pct"]
    bb_width    = row["bb_width"]
    adx         = row["adx"]
    plus_di     = row["plus_di"]
    minus_di    = row["minus_di"]
    vol_ratio   = row["vol_ratio"]

    # ── 4. Warmup & Regime Filter ──
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"
    
    if adx < 16 and bb_width < 0.012:
        return "HOLD"

    # ── 5. EXIT Logic ──
    MIN_HOLD = 3
    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)
        
        trailing_hit = unrealized < (_max_favorable - atr_pct*1.5) and _max_favorable > 0.3
        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (macd_accel < 0)
        rsi_extreme  = rsi > 78
        di_flip      = (minus_di > plus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)
        
        trailing_hit = unrealized < (_max_favorable - atr_pct*1.5) and _max_favorable > 0.3
        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (macd_accel > 0)
        rsi_extreme  = rsi < 22
        di_flip      = (plus_di > minus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "BUY"

    # ── 6. ENTRY Logic ──
    COOLDOWN = 4
    if pos_type == "NONE" and _candles_since_exit >= COOLDOWN:
        # LONG check
        long_score = 0
        if price > ema200 and ema21 > ema55:   long_score += 1
        if macd > macd_sig and macd_accel > 0: long_score += 1
        if stoch_k > stoch_d and stoch_k < 70 and rsi > 45: long_score += 1
        if adx > 20 and plus_di > minus_di and ema21_slope > 0.03: long_score += 1
        if vol_ratio >= 1.2:                   long_score += 1

        if long_score >= 3:
            return "BUY"

        # SHORT check
        short_score = 0
        if price < ema200 and ema21 < ema55:   short_score += 1
        if macd < macd_sig and macd_accel < 0: short_score += 1
        if stoch_k < stoch_d and stoch_k > 30 and rsi < 55: short_score += 1
        if adx > 20 and minus_di > plus_di and ema21_slope < -0.03: short_score += 1
        if vol_ratio >= 1.2:                   short_score += 1

        if short_score >= 3:
            return "SELL"
            
    return "HOLD"
