import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  CLAUDE OPUS 4.6 V2 — "ADAPTIVE QUANTUM MOMENTUM"
# ═══════════════════════════════════════════════════════════════════
#  Evolusi dari CLAUDE-OPUS-4.6 (Champion: +92.04% ROI / 374 hari)
#
#  UPGRADE LOG V2:
#  ┌────────────────────────────────────────────────────────────────┐
#  │ #1  Dynamic Trailing Stop (ADX-based multiplier)              │
#  │ #2  Adaptive Cooldown (trend-aware re-entry)                  │
#  │ #3  Short Bias Filter (BTC bull market protection)            │
#  │ #4  Adaptive RSI Exit (ADX-scaled threshold)                  │
#  │ #5  Keltner Channel Squeeze Detector (breakout bonus)         │
#  │ #6  Profit Lock Mechanism (tighten trail after target hit)    │
#  └────────────────────────────────────────────────────────────────┘
#
#  BASE: Opus 4.6 (EMA200 + StochRSI + MACD + ADX + Volume)
#  TARGET: ROI > 92% dalam 374 hari
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE TRACKER ───
_candles_in_pos = 0
_candles_since_exit = 99
_last_pos_type = "NONE"
_entry_price = 0.0
_max_favorable = 0.0
_profit_locked = False  # V2: Profit lock flag


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1: INDICATOR ENGINE (Opus Base + V2 Keltner Squeeze)
# ═══════════════════════════════════════════════════════════════════
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # ═══ LAYER 1: TREND STRUCTURE ═══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # Trend Acceleration (slope differential)
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan) * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["trend_accel"] = df["ema9_slope"] - df["ema21_slope"]

    # ═══ LAYER 2: MOMENTUM ═══
    # RSI-14 (Classic)
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag    = gain.ewm(com=13, adjust=False).mean()
    al    = loss.ewm(com=13, adjust=False).mean()
    rs    = ag / al.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Stochastic RSI — timing presisi entry
    rsi_series = df["rsi"]
    rsi_min = rsi_series.rolling(14).min()
    rsi_max = rsi_series.rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((rsi_series - rsi_min) / rsi_range) * 100
    df["stoch_rsi_k"] = stoch_k.rolling(3).mean()
    df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()

    # MACD (12/26/9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema12 - ema26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # ═══ LAYER 3: VOLATILITY ═══
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100

    # Bollinger Band (20, 2)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # ═══ V2 NEW: KELTNER CHANNEL (20, 1.5x ATR) ═══
    kc_mid = c.ewm(span=20, adjust=False).mean()
    kc_atr = df["atr"]
    df["kc_upper"] = kc_mid + 1.5 * kc_atr
    df["kc_lower"] = kc_mid - 1.5 * kc_atr

    # Squeeze Detection: BB inside KC = squeeze (volatilitas sangat rendah)
    df["squeeze_on"] = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
    # Squeeze Release: saat squeeze baru saja lepas
    df["squeeze_release"] = (~df["squeeze_on"]) & (df["squeeze_on"].shift(1).fillna(False))

    # ═══ LAYER 4: TREND STRENGTH (ADX) ═══
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

    # ═══ LAYER 5: VOLUME INTELLIGENCE ═══
    df["vol_ma20"]  = v.rolling(20).mean()
    df["vol_ratio"] = v / df["vol_ma20"].replace(0, np.nan)
    df["vol_rising"] = (v > v.shift(1)) & (v.shift(1) > v.shift(2))

    return df.fillna(0)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2: SIGNAL BRAIN — ADAPTIVE QUANTUM MOMENTUM V2
# ═══════════════════════════════════════════════════════════════════
def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable, _profit_locked

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
        _profit_locked = False
    elif pos_type == "NONE" and _last_pos_type == "NONE":
        _candles_since_exit = min(_candles_since_exit + 1, 99)
    elif pos_type != "NONE" and _last_pos_type == "NONE":
        _candles_in_pos = 1
        _entry_price = row["close"]
        _max_favorable = 0.0
        _profit_locked = False

    _last_pos_type = pos_type

    # ─── 3. Extract Variables ───
    price       = row["close"]
    ema9        = row["ema_9"]
    ema21       = row["ema_21"]
    ema55       = row["ema_55"]
    ema200      = row["ema_200"]
    ema21_slope = row["ema21_slope"]
    trend_accel = row["trend_accel"]
    rsi         = row["rsi"]
    stoch_k     = row["stoch_rsi_k"]
    stoch_d     = row["stoch_rsi_d"]
    macd        = row["macd"]
    macd_sig    = row["macd_sig"]
    macd_hist   = row["macd_hist"]
    macd_accel  = row["macd_accel"]
    atr_pct     = row["atr_pct"]
    bb_width    = row["bb_width"]
    adx         = row["adx"]
    plus_di     = row["plus_di"]
    minus_di    = row["minus_di"]
    vol_ratio   = row["vol_ratio"]
    squeeze_rel = row["squeeze_release"]

    # ─── 4. Warmup Guard ───
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"

    # ─── 5. Market Regime Filter ───
    # Tetap pakai AND (bukan OR seperti GROK yang gagal)
    if adx < 16 and bb_width < 0.012:
        return "HOLD"

    # ═══════════════════════════════════════════
    # 6. EXIT LOGIC — V2 DYNAMIC TRAILING + ADAPTIVE RSI
    # ═══════════════════════════════════════════
    MIN_HOLD = 3

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # V2: DYNAMIC TRAILING STOP (ADX-based multiplier)
        if adx > 30:
            trail_mult = 2.0    # Strong trend: biarkan run
        elif adx > 20:
            trail_mult = 1.5    # Moderate: standar Opus
        else:
            trail_mult = 1.0    # Weak trend: cepat ambil profit

        # V2: PROFIT LOCK — setelah capai ATR × 2, ketatkan trailing
        if _max_favorable > atr_pct * 2.0:
            _profit_locked = True
        if _profit_locked:
            trail_mult = min(trail_mult, 1.0)  # Force tight trail

        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.3

        # EXIT CONDITION 2: Trend Structure Breakdown
        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (macd_accel < 0)

        # V2: ADAPTIVE RSI EXIT (ADX-scaled)
        rsi_exit_threshold = 82 if adx > 30 else 75
        rsi_extreme = rsi > rsi_exit_threshold

        # EXIT CONDITION 4: DI Crossover (bearish takeover)
        di_flip = (minus_di > plus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # V2: Dynamic Trailing (same logic)
        if adx > 30:
            trail_mult = 2.0
        elif adx > 20:
            trail_mult = 1.5
        else:
            trail_mult = 1.0

        if _max_favorable > atr_pct * 2.0:
            _profit_locked = True
        if _profit_locked:
            trail_mult = min(trail_mult, 1.0)

        trailing_hit = unrealized < (_max_favorable - atr_pct * trail_mult) and _max_favorable > 0.3

        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (macd_accel > 0)

        rsi_exit_threshold = 18 if adx > 30 else 25
        rsi_extreme = rsi < rsi_exit_threshold

        di_flip = (plus_di > minus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "BUY"

    # ═══════════════════════════════════════════
    # 7. ENTRY LOGIC — V2 ADAPTIVE COOLDOWN + SQUEEZE BONUS
    # ═══════════════════════════════════════════

    # V2: ADAPTIVE COOLDOWN
    if pos_type == "NONE":
        # Trend-aware cooldown
        if trend_accel > 0.02 and ema9 > ema21:
            # Momentum kuat searah → cepat re-entry
            cooldown = 3
        elif trend_accel < -0.02 and ema9 < ema21:
            # Momentum kuat bearish → cepat re-entry short
            cooldown = 3
        else:
            # Tidak jelas → lebih hati-hati
            cooldown = 5

        if _candles_since_exit < cooldown:
            return "HOLD"

    if pos_type == "NONE":
        # ── LONG CONFLUENCE SCORING ──
        long_score = 0

        # [KUNCI #1] Major Trend (dari GeminiPro — paling dominan)
        if price > ema200 and ema21 > ema55:
            long_score += 1

        # [KUNCI #2] Momentum Acceleration
        if macd > macd_sig and macd_accel > 0:
            long_score += 1

        # [KUNCI #3] Stochastic RSI Timing
        if stoch_k > stoch_d and stoch_k < 70 and rsi > 45:
            long_score += 1

        # [KUNCI #4] Trend Strength + Direction
        if adx > 20 and plus_di > minus_di and ema21_slope > 0.03:
            long_score += 1

        # [KUNCI #5] Volume Confirmation
        if vol_ratio >= 1.2:
            long_score += 1

        # V2: SQUEEZE RELEASE BONUS (+1 saat volatilitas meledak)
        if squeeze_rel and trend_accel > 0:
            long_score += 1

        # Threshold: 3 dari 5 (atau 6 dengan squeeze bonus)
        if long_score >= 3:
            return "BUY"

        # ── SHORT CONFLUENCE SCORING ──
        short_score = 0

        # V2: SHORT BIAS FILTER — tambah syarat EMA55 < EMA200
        if price < ema200 and ema21 < ema55 and ema55 < ema200:
            short_score += 1

        if macd < macd_sig and macd_accel < 0:
            short_score += 1

        if stoch_k < stoch_d and stoch_k > 30 and rsi < 55:
            short_score += 1

        if adx > 20 and minus_di > plus_di and ema21_slope < -0.03:
            short_score += 1

        if vol_ratio >= 1.2:
            short_score += 1

        # V2: Squeeze release bonus for short
        if squeeze_rel and trend_accel < 0:
            short_score += 1

        # V2: Short threshold KETAT → 4 dari 5/6 (BTC bull bias protection)
        if short_score >= 4:
            return "SELL"

    return "HOLD"
