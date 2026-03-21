import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  CLAUDE OPUS 4.6 — "ADAPTIVE MOMENTUM HUNTER"
# ═══════════════════════════════════════════════════════════════════
#  Dirancang oleh AI Claude berdasarkan analisis performa 4 strategi:
#
#  TRAINING DATA ANALYSIS (history_trade.csv):
#  ┌─────────────────────┬──────────┬────────────────────────────────┐
#  │ Strategy            │ ROI      │ Diagnosis                      │
#  ├─────────────────────┼──────────┼────────────────────────────────┤
#  │ GEMINIPRO           │ +45.24%  │ Juara. EMA200 + RSI momentum   │
#  │ GEMINIFLASH         │ +25.50%  │ Triple EMA bagus, RSI terlalu  │
#  │                     │          │ longgar → overtrade             │
#  │ CHATGPT             │ +16.29%  │ BB mean-reversion jarang fire  │
#  │                     │          │ di trending market              │
#  │ CLAUDE-SONNET-4.6   │ +12.17%  │ Terlalu defensive. Gate 4/5    │
#  │                     │          │ konfirmasi = terlalu sedikit    │
#  │                     │          │ entry                           │
#  └─────────────────────┴──────────┴────────────────────────────────┘
#
#  ARSITEKTUR OPUS (Hybrid Adaptive):
#  - DARI GEMINIPRO  : EMA200 Major Trend Filter (kunci kemenangan)
#  - DARI SONNET     : ADX Trend Strength + Volume Spike Confirmation
#  - BARU (OPUS)     : Stochastic RSI untuk timing presisi
#  - BARU (OPUS)     : Adaptive Threshold (3/5 bukan 4/5)
#  - BARU (OPUS)     : Trailing Mental Stop (ATR-based exit)
#  - BARU (OPUS)     : Trend Acceleration Detector (EMA slope diff)
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE TRACKER ───
_candles_in_pos = 0
_candles_since_exit = 99
_last_pos_type = "NONE"
_entry_price = 0.0
_max_favorable = 0.0  # Track best PnL for trailing stop


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1: INDICATOR ENGINE (Custom Built, No External TA Lib)
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
    df["trend_accel"] = df["ema9_slope"] - df["ema21_slope"]  # Positive = accelerating up

    # ═══ LAYER 2: MOMENTUM ═══
    # RSI-14 (Classic)
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag    = gain.ewm(com=13, adjust=False).mean()
    al    = loss.ewm(com=13, adjust=False).mean()
    rs    = ag / al.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # Stochastic RSI (Opus Exclusive) — timing presisi entry
    rsi_series = df["rsi"]
    rsi_min = rsi_series.rolling(14).min()
    rsi_max = rsi_series.rolling(14).max()
    rsi_range = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((rsi_series - rsi_min) / rsi_range) * 100
    df["stoch_rsi_k"] = stoch_k.rolling(3).mean()  # Smoothed %K
    df["stoch_rsi_d"] = df["stoch_rsi_k"].rolling(3).mean()  # %D signal

    # MACD (12/26/9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema12 - ema26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]

    # MACD Momentum Direction (2-candle consecutive)
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # ═══ LAYER 3: VOLATILITY ═══
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100

    # Bollinger Band Width (squeeze detector)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

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

    # Volume Trend (apakah volume meningkat selama 3 bar terakhir)
    df["vol_rising"] = (v > v.shift(1)) & (v.shift(1) > v.shift(2))

    return df.fillna(0)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2: SIGNAL BRAIN — ADAPTIVE MOMENTUM HUNTER
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

    # ─── 4. Warmup Guard ───
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"

    # ─── 5. Market Regime Filter ───
    # Kunci: Jangan trade di market mati (low ADX + narrow BB)
    if adx < 16 and bb_width < 0.012:
        return "HOLD"

    # ═══════════════════════════════════════════
    # 6. EXIT LOGIC (Adaptive Trailing + Reversal)
    # ═══════════════════════════════════════════
    MIN_HOLD = 3  # Lebih cepat dari Sonnet (4) tapi tetap ada buffer

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        # Track max favorable excursion
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # EXIT CONDITION 1: ATR Trailing Stop (berikan 1.5x ATR ruang gerak)
        trailing_hit = unrealized < (_max_favorable - atr_pct * 1.5) and _max_favorable > 0.3

        # EXIT CONDITION 2: Trend Structure Breakdown
        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (macd_accel < 0)

        # EXIT CONDITION 3: RSI Extreme
        rsi_extreme = rsi > 78

        # EXIT CONDITION 4: DI Crossover (bearish takeover)
        di_flip = (minus_di > plus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        trailing_hit = unrealized < (_max_favorable - atr_pct * 1.5) and _max_favorable > 0.3
        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (macd_accel > 0)
        rsi_extreme = rsi < 22
        di_flip = (plus_di > minus_di + 5) and adx > 20

        if trailing_hit or (trend_broken and di_flip) or rsi_extreme:
            return "BUY"

    # ═══════════════════════════════════════════
    # 7. ENTRY LOGIC (Adaptive 3/5 Confluence)
    # ═══════════════════════════════════════════
    COOLDOWN = 4  # Lebih pendek dari Sonnet (6) agar tidak terlalu lambat

    if pos_type == "NONE" and _candles_since_exit < COOLDOWN:
        return "HOLD"

    if pos_type == "NONE":
        # ── LONG CONFLUENCE SCORING ──
        long_score = 0

        # [KUNCI #1] Major Trend (dari GeminiPro — factor paling dominan)
        if price > ema200 and ema21 > ema55:
            long_score += 1

        # [KUNCI #2] Momentum Acceleration
        if macd > macd_sig and macd_accel > 0:
            long_score += 1

        # [KUNCI #3] Stochastic RSI Timing (Opus Exclusive)
        # Entry saat StochRSI golden cross dari oversold zone
        if stoch_k > stoch_d and stoch_k < 70 and rsi > 45:
            long_score += 1

        # [KUNCI #4] Trend Strength + Direction
        if adx > 20 and plus_di > minus_di and ema21_slope > 0.03:
            long_score += 1

        # [KUNCI #5] Volume Confirmation
        if vol_ratio >= 1.2:
            long_score += 1

        # Threshold: 3 dari 5 (lebih agresif dari Sonnet 4/5)
        if long_score >= 3:
            return "BUY"

        # ── SHORT CONFLUENCE SCORING ──
        short_score = 0

        if price < ema200 and ema21 < ema55:
            short_score += 1

        if macd < macd_sig and macd_accel < 0:
            short_score += 1

        if stoch_k < stoch_d and stoch_k > 30 and rsi < 55:
            short_score += 1

        if adx > 20 and minus_di > plus_di and ema21_slope < -0.03:
            short_score += 1

        if vol_ratio >= 1.2:
            short_score += 1

        if short_score >= 3:
            return "SELL"

    return "HOLD"
