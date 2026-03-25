import pandas as pd
import numpy as np

# ══════════════════════════════════════════════════════════════════════
#  VERSAAGONON-PRO-1H — Strategi scalping 1 jam
#  Menggabungkan EMA, MACD, StochRSI, ADX, Volume, Squeeze untuk rasio profit:loss ≥5:1
# ══════════════════════════════════════════════════════════════════════

# ─── Internal State Tracking ───
_candles_in_pos     = 0
_candles_since_exit = 99
_last_pos_type      = "NONE"
_entry_price        = 0.0
_max_favorable      = 0.0
_be_active          = False   # Flag untuk break-even

# ─── Bagian 1: Hitung indikator teknikal ───
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # ═══ LAYER 1: MOVING AVERAGES (EMA) ═══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # ═══ LAYER 2: MOMENTUM (RSI, StochRSI) ═══
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    # Stochastic RSI
    rsi_min = df["rsi"].rolling(14).min()
    rsi_max = df["rsi"].rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((df["rsi"] - rsi_min) / rsi_range) * 100
    df["stoch_k"] = stoch_k.rolling(3).mean()
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # ═══ LAYER 3: MOMENTUM LANJUT (MACD) ═══
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"] = ema12 - ema26
    df["macd_sig"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # ═══ LAYER 4: VOLATILITY (ATR) + BB/KC Squeeze ═══
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"] = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100
    # Bollinger Bands
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)
    # Keltner Channels
    kc_mid = c.ewm(span=20, adjust=False).mean()
    df["kc_upper"] = kc_mid + 1.5 * df["atr"]
    df["kc_lower"] = kc_mid - 1.5 * df["atr"]
    # Squeeze on/off
    df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
    df["squeeze_release"] = (~df["squeeze_on"]) & (df["squeeze_on"].shift(1).fillna(False))

    # ═══ LAYER 5: TREND STRENGTH (ADX & DI) ═══
    up = h - h.shift(1)
    down = l.shift(1) - l
    pdm = np.where((up > down) & (up > 0), up, 0.0)
    mdm = np.where((down > up) & (down > 0), down, 0.0)
    atr_s = tr.ewm(com=13, adjust=False).mean()
    pdi = 100 * pd.Series(pdm).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi = 100 * pd.Series(mdm).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    df["adx"] = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"] = pdi
    df["minus_di"] = mdi

    # ═══ LAYER 6: VOLUME ═══
    df["vol_ma20"] = v.rolling(20).mean()
    df["vol_ratio"] = v / df["vol_ma20"].replace(0, np.nan)

    return df.fillna(0)


# ─── Bagian 2: Logika Sinyal ENTRY/EXIT ───
def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type, _entry_price, _max_favorable, _be_active

    # ─── 1. State Machine ───
    pos_type = position.get("type", "NONE") if position else "NONE"
    # Update counters
    if pos_type != "NONE" and _last_pos_type != "NONE":
        _candles_in_pos += 1
    elif pos_type == "NONE" and _last_pos_type != "NONE":
        _candles_since_exit = 0
        _candles_in_pos = 0
        _entry_price = 0.0
        _max_favorable = 0.0
        _be_active = False
    elif pos_type == "NONE" and _last_pos_type == "NONE":
        _candles_since_exit = min(_candles_since_exit + 1, 99)
    else:  # baru masuk posisi
        _candles_in_pos = 1
        _entry_price = row["close"]
        _max_favorable = 0.0
        _be_active = False

    _last_pos_type = pos_type

    # ─── 2. Ekstrak variabel indikator ───
    price       = row["close"]
    ema9        = row["ema_9"]
    ema21       = row["ema_21"]
    ema55       = row["ema_55"]
    ema200      = row["ema_200"]
    rsi         = row["rsi"]
    stoch_k     = row["stoch_k"]
    stoch_d     = row["stoch_d"]
    macd        = row["macd"]
    macd_sig    = row["macd_sig"]
    macd_accel  = row["macd_accel"]
    atr_pct     = row["atr_pct"]
    bb_width    = row["bb_width"]
    adx         = row["adx"]
    plus_di     = row["plus_di"]
    minus_di    = row["minus_di"]
    vol_ratio   = row["vol_ratio"]
    squeeze_rel = row["squeeze_release"]

    # ─── 3. Warmup Guard ───
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"

    # ─── 4. Market Regime Filter ───
    if adx < 16 and bb_width < 0.012:
        return "HOLD"

    # ─── 5. EXIT LOGIC: Trailing + Break-even + Reversal ───
    MIN_HOLD = 3
    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)
        # Trailing multiplier adaptif (berbasis ADX)
        if adx > 35:
            trail_mult = 2.5
        elif adx > 25:
            trail_mult = 1.5
        else:
            trail_mult = 1.0
        # Aktifkan break-even jika profit besar
        if unrealized > (atr_pct * 1.8):
            _be_active = True
        # Cek trailing stop, break-even, atau stop keras
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4
        be_hit = _be_active and price < (_entry_price * 1.001)   # jika turun kembali ke ~entry
        hard_stop = unrealized < -(atr_pct * 1.5)              # kerugian melebihi 1.5x ATR
        trend_reverse = (ema9 < ema21) and (macd < macd_sig) and (_candles_in_pos > 3)
        rsi_extreme = rsi > 84
        if trailing_hit or be_hit or hard_stop or trend_reverse or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)
        if adx > 35:
            trail_mult = 2.5
        elif adx > 25:
            trail_mult = 1.5
        else:
            trail_mult = 1.0
        if unrealized > (atr_pct * 1.8):
            _be_active = True
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4
        be_hit = _be_active and price > (_entry_price * 0.999)   # jika naik kembali ke ~entry
        hard_stop = unrealized < -(atr_pct * 1.5)
        trend_reverse = (ema9 > ema21) and (macd > macd_sig) and (_candles_in_pos > 3)
        rsi_extreme = rsi < 16
        if trailing_hit or be_hit or hard_stop or trend_reverse or rsi_extreme:
            return "BUY"

    # ─── 6. ENTRY LOGIC: Scoring Confluence ───
    COOLDOWN = 3
    if pos_type != "NONE" or _candles_since_exit < COOLDOWN:
        return "HOLD"

    long_score = 0
    if price > ema200 and ema21 > ema55:
        long_score += 1
    if macd > macd_sig and macd_accel > 0:
        long_score += 1
    if stoch_k > stoch_d and stoch_k < 70 and rsi > 45:
        long_score += 1
    if adx > 20 and plus_di > minus_di:
        long_score += 1
    if vol_ratio >= 1.2:
        long_score += 1
    if squeeze_rel and adx > 20:
        long_score += 1
    if long_score >= 4:
        return "BUY"

    short_score = 0
    if price < ema200 and ema21 < ema55:
        short_score += 1
    if macd < macd_sig and macd_accel < 0:
        short_score += 1
    if stoch_k < stoch_d and stoch_k > 30 and rsi < 55:
        short_score += 1
    if adx > 20 and minus_di > plus_di:
        short_score += 1
    if vol_ratio >= 1.2:
        short_score += 1
    if squeeze_rel and adx > 20:
        short_score += 1
    if short_score >= 4:
        return "SELL"

    return "HOLD"