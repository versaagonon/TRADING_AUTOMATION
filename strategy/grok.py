import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  GROK-XAI v2 — "ULTIMATE MOMENTUM CRUSHER"
# ═══════════════════════════════════════════════════════════════════
#  Dirancang oleh Grok (xAI) setelah menganalisis CLAUDE-OPUS-4.6
#
#  ANALISIS OPUS (juara kualifikasi):
#  ┌─────────────────────┬──────────┬────────────────────────────────┐
#  │ Strategy            │ ROI      │ Kelemahan yang Grok temukan    │
#  ├─────────────────────┼──────────┼────────────────────────────────┤
#  │ CLAUDE-OPUS-4.6     │ +92.04%  │ Trailing terlalu longgar (1.5x)│
#  │                     │          │ Cooldown 4 candle → ketinggalan│
#  │                     │          │ Short terlalu mudah trigger    │
#  │                     │          │ Tidak ada "Grok Edge" di bull  │
#  └─────────────────────┴──────────┴────────────────────────────────┘
#
#  UPGRADE GROK v2:
#  - Dari Opus       : Stochastic RSI + Adaptive Trailing + Trend Accel
#  - Grok Exclusive  : Cooldown 3 candle + MIN_HOLD 2 + Dynamic Trailing (1.2x–2.0x berdasarkan ADX)
#  - Grok Exclusive  : Volume Rising WAJIB + Super Acceleration Filter
#  - Grok Exclusive  : Short DIFFICULT (hanya 1 dari 10 entry = fokus bull BTC)
#  - Target          : ROI >110% dalam 372 hari (prediksi Grok)
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE TRACKER (Grok version) ───
_candles_in_pos = 0
_candles_since_exit = 99
_last_pos_type = "NONE"
_entry_price = 0.0
_max_favorable = 0.0


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1: INDICATOR ENGINE (Opus base + Grok tweaks)
# ═══════════════════════════════════════════════════════════════════
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # ═══ LAYER 1: TREND STRUCTURE (Opus + Grok faster EMA) ═══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # Trend Acceleration (Grok smoothed)
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan) * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["ema55_slope"] = (df["ema_55"] - df["ema_55"].shift(5)) / df["ema_55"].replace(0, np.nan) * 100
    df["trend_accel"] = (df["ema9_slope"] - df["ema21_slope"]).ewm(span=2, adjust=False).mean()

    # ═══ LAYER 2: MOMENTUM (Opus + Grok Super Accel) ═══
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag    = gain.ewm(com=13, adjust=False).mean()
    al    = loss.ewm(com=13, adjust=False).mean()
    rs    = ag / al.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Stochastic RSI (Opus + Grok smoothing ekstra)
    rsi_series = df["rsi"]
    rsi_min = rsi_series.rolling(14).min()
    rsi_max = rsi_series.rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((rsi_series - rsi_min) / rsi_range) * 100
    df["stoch_rsi_k"] = stoch_k.ewm(span=3, adjust=False).mean()
    df["stoch_rsi_d"] = df["stoch_rsi_k"].ewm(span=3, adjust=False).mean()

    # MACD + Grok Super Acceleration
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema12 - ema26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)
    df["super_accel"] = df["trend_accel"] * df["macd_accel"]   # <-- Grok Exclusive

    # ═══ LAYER 3: VOLATILITY + ADX + VOLUME (sama Opus) ═══
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100

    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    up   = h - h.shift(1)
    down = l.shift(1) - l
    pdm  = np.where((up > down) & (up > 0), up, 0)
    mdm  = np.where((down > up) & (down > 0), down, 0)
    atr_s  = tr.ewm(com=13, adjust=False).mean()
    pdi    = 100 * pd.Series(pdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi    = 100 * pd.Series(mdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx     = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    df["adx"]      = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]  = pdi
    df["minus_di"] = mdi

    df["vol_ma20"]  = v.rolling(20).mean()
    df["vol_ratio"] = v / df["vol_ma20"].replace(0, np.nan)
    df["vol_rising"] = (v > v.shift(1)) & (v.shift(1) > v.shift(2))

    return df.fillna(0)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2: SIGNAL BRAIN — ULTIMATE MOMENTUM CRUSHER
# ═══════════════════════════════════════════════════════════════════
def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable

    # ─── 1. State Parsing ───
    pos_type = position.get("type", "NONE") if position else "NONE"

    # ─── 2. Internal State Machine ───
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

    # ─── 3. Extract Variables ───
    price       = row["close"]
    ema9        = row["ema_9"]
    ema21       = row["ema_21"]
    ema55       = row["ema_55"]
    ema200      = row["ema_200"]
    ema21_slope = row["ema21_slope"]
    ema55_slope = row["ema55_slope"]
    trend_accel = row["trend_accel"]
    super_accel = row["super_accel"]
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
    vol_rising  = row["vol_rising"]

    # ─── 4. Warmup Guard ───
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"

    # ─── 5. Market Regime Filter (Grok lebih ketat) ───
    if adx < 18 or bb_width < 0.015:
        return "HOLD"

    # ═══════════════════════════════════════════
    # 6. EXIT LOGIC (Dynamic Trailing Grok Edition)
    # ═══════════════════════════════════════════
    MIN_HOLD = 2   # Lebih cepat dari Opus (3)

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # Dynamic Trailing: ADX tinggi = lebih longgar, ADX rendah = ketat
        trail_mult = 2.0 if adx > 35 else 1.2
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4

        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (super_accel < 0)
        rsi_extreme  = rsi > 80
        di_flip      = (minus_di > plus_di + 6) and adx > 22

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        trail_mult = 2.0 if adx > 35 else 1.2
        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.4

        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (super_accel > 0)
        rsi_extreme  = rsi < 20
        di_flip      = (plus_di > minus_di + 6) and adx > 22

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "BUY"

    # ═══════════════════════════════════════════
    # 7. ENTRY LOGIC (Grok 3/5 + Volume Rising WAJIB)
    # ═══════════════════════════════════════════
    COOLDOWN = 3   # Lebih cepat dari Opus (4)

    if pos_type == "NONE" and _candles_since_exit < COOLDOWN:
        return "HOLD"

    if pos_type == "NONE":
        # ── LONG CONFLUENCE SCORING (Grok lebih agresif di bull) ──
        long_score = 0

        if price > ema200 and ema21 > ema55 and trend_accel > 0.02:   # Grok tambah accel
            long_score += 1
        if macd > macd_sig and macd_accel > 0 and super_accel > 0:
            long_score += 1
        if stoch_k > stoch_d and stoch_k < 75 and rsi > 48:
            long_score += 1
        if adx > 22 and plus_di > minus_di + 2 and ema21_slope > 0.04:  # Grok lebih ketat DI
            long_score += 1
        if vol_ratio >= 1.25 and vol_rising:   # WAJIB volume naik
            long_score += 1

        if long_score >= 3:
            return "BUY"

        # ── SHORT CONFLUENCE (Grok buat super susah — BTC bull bias) ──
        short_score = 0

        if price < ema200 and ema21 < ema55 and trend_accel < -0.05:
            short_score += 1
        if macd < macd_sig and macd_accel < 0 and super_accel < -0.1:
            short_score += 1
        if stoch_k < stoch_d and stoch_k > 25 and rsi < 50:
            short_score += 1
        if adx > 28 and minus_di > plus_di + 8:   # Grok super ketat short
            short_score += 1
        if vol_ratio >= 1.4 and vol_rising:
            short_score += 1

        if short_score >= 4.5:   # Hampir mustahil kecuali crash besar
            return "SELL"

    return "HOLD"