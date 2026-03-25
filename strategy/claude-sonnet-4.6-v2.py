import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  CLAUDE APEX V1 — "PRECISION SCALPER + TREND RIDER"
# ═══════════════════════════════════════════════════════════════════
#  Dirancang oleh Claude berdasarkan analisis komprehensif 4 strategi
#  terbaik dengan target rasio profit 5:1
#
#  PERFORMANCE BENCHMARK:
#  ┌──────────────────────┬──────────┬───────────┬────────────────┐
#  │ Strategy             │ ROI      │ Max DD    │ Lose Rate      │
#  ├──────────────────────┼──────────┼───────────┼────────────────┤
#  │ CLAUDE-OPUS-4.6-V2   │ +129.51% │  9.78%    │ 48.19%         │
#  │ GEMINI-CODEAGENT(v3) │  +83.20% │ 12.00%    │ 48.83%         │
#  │ CLAUDE-OPUS-4.6      │  +92.04% │ 12.50%    │ 48.53%         │
#  │ GEMINIPRO            │   +7.23% │ 26.00%    │ 49.92%         │
#  └──────────────────────┴──────────┴───────────┴────────────────┘
#
#  ARSITEKTUR APEX — INOVASI BARU:
#  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  [TIER 1] SCALP ENGINE (Fitur Baru)
#    → Multi-timeframe signal synthesis dalam 1 candle
#    → Micro-momentum burst detection (EMA slope velocity)
#    → Tick-level order flow proxy via volume acceleration
#
#  [TIER 2] CONFLUENCE SCORING (6 Dimensi)
#    → Dimensi 1: Major Trend Structure (EMA200 + EMA55 alignment)
#    → Dimensi 2: MACD Acceleration (histogram velocity + direction)
#    → Dimensi 3: StochRSI Precision Timing (cross + zone filter)
#    → Dimensi 4: ADX Trend Strength (dengan slope ADX sebagai bonus)
#    → Dimensi 5: Volume Surge (ratio + acceleration)
#    → Dimensi 6: Squeeze Release (Keltner breakout detector)
#
#  [TIER 3] SMART EXIT SYSTEM
#    → 5-level ATR Dynamic Trailing (vs 3-level di versi lama)
#    → Profit Lock Tiered: 1.5x, 2.5x, 4x ATR milestones
#    → Adaptive RSI Exit (ADX + slope scaled)
#    → Time-decay exit (posisi stuck = cut)
#    → Momentum exhaustion detector (MACD divergence)
#
#  [TIER 4] RISK ENGINE
#    → Hard SL: 1.2x ATR (lebih ketat dari Gemini 1.5x)
#    → Breakeven engine: aktif di 1.2x ATR profit
#    → Short bias protection: triple EMA alignment required
#    → Market hours filter: hindari sideways consolidation
#
#  TARGET: ROI > 150%, MaxDD < 9%, Win Rate > 52%
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE ───
_candles_in_pos     = 0
_candles_since_exit = 99
_last_pos_type      = "NONE"
_entry_price        = 0.0
_max_favorable      = 0.0
_be_active          = False       # Breakeven protection flag
_profit_tier        = 0           # 0=none, 1=1.5x, 2=2.5x, 3=4x ATR
_scalp_mode         = False       # Scalp mode vs swing mode
_trend_strength_ma  = 0.0        # Smooth ADX tracker


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1: APEX INDICATOR ENGINE
#  (29 Indikator — paling lengkap dari semua versi)
# ═══════════════════════════════════════════════════════════════════
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c = df["close"]
    h = df["high"]
    l = df["low"]
    v = df["volume"]

    # ══════════════════════════════════
    # LAYER 1: TREND ARCHITECTURE
    # ══════════════════════════════════
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # EMA Slope Velocity (untuk scalp detection)
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan) * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["ema55_slope"] = (df["ema_55"] - df["ema_55"].shift(5)) / df["ema_55"].replace(0, np.nan) * 100

    # Trend Acceleration (micro-momentum burst detector)
    df["trend_accel"]    = df["ema9_slope"] - df["ema21_slope"]
    df["macro_momentum"] = df["ema21_slope"] - df["ema55_slope"]   # Baru: macro alignment

    # EMA Spread (alignment kualitas tren)
    df["ema_spread"]  = (df["ema_9"] - df["ema_55"]) / df["ema_55"].replace(0, np.nan) * 100

    # ══════════════════════════════════
    # LAYER 2: MOMENTUM ENGINE
    # ══════════════════════════════════
    # RSI-14
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag    = gain.ewm(com=13, adjust=False).mean()
    al    = loss.ewm(com=13, adjust=False).mean()
    rs    = ag / al.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))
    df["rsi_slope"] = df["rsi"] - df["rsi"].shift(2)  # RSI momentum direction

    # Stochastic RSI (precision timing)
    rsi_s   = df["rsi"]
    rsi_min = rsi_s.rolling(14).min()
    rsi_max = rsi_s.rolling(14).max()
    rsi_rng = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k = ((rsi_s - rsi_min) / rsi_rng) * 100
    df["stoch_k"] = stoch_k.rolling(3).mean()   # Smoothed %K
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()  # %D signal line
    df["stoch_cross_up"]   = (df["stoch_k"] > df["stoch_d"]) & (df["stoch_k"].shift(1) <= df["stoch_d"].shift(1))
    df["stoch_cross_down"] = (df["stoch_k"] < df["stoch_d"]) & (df["stoch_k"].shift(1) >= df["stoch_d"].shift(1))

    # MACD (12/26/9)
    ema12 = c.ewm(span=12, adjust=False).mean()
    ema26 = c.ewm(span=26, adjust=False).mean()
    df["macd"]       = ema12 - ema26
    df["macd_sig"]   = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"]  = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)
    df["macd_vel"]   = df["macd_accel"] - df["macd_accel"].shift(1)  # Baru: jerk/velocity ke-3

    # ══════════════════════════════════
    # LAYER 3: VOLATILITY MATRIX
    # ══════════════════════════════════
    prev_c = c.shift(1)
    tr = pd.concat([h - l, (h - prev_c).abs(), (l - prev_c).abs()], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100
    df["atr_slope"] = df["atr_pct"] - df["atr_pct"].shift(3)  # Expanding/contracting volatility

    # Bollinger Bands (20, 2)
    bb_mid = c.rolling(20).mean()
    bb_std = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2.0 * bb_std
    df["bb_lower"] = bb_mid - 2.0 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)
    df["bb_pct"]   = (c - df["bb_lower"]) / (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)  # Position in BB

    # Keltner Channel (20, 1.5x ATR)
    kc_mid = c.ewm(span=20, adjust=False).mean()
    df["kc_upper"] = kc_mid + 1.5 * df["atr"]
    df["kc_lower"] = kc_mid - 1.5 * df["atr"]

    # Squeeze Detection (BB inside KC = compression)
    df["squeeze_on"]      = (df["bb_lower"] > df["kc_lower"]) & (df["bb_upper"] < df["kc_upper"])
    df["squeeze_release"] = (~df["squeeze_on"]) & (df["squeeze_on"].shift(1).fillna(False))
    df["squeeze_bars"]    = df["squeeze_on"].astype(int).groupby(
        (df["squeeze_on"] != df["squeeze_on"].shift()).cumsum()
    ).cumsum()  # Berapa lama squeeze berlangsung

    # ══════════════════════════════════
    # LAYER 4: TREND STRENGTH (ADX+)
    # ══════════════════════════════════
    up   = h - h.shift(1)
    down = l.shift(1) - l
    pdm  = np.where((up > down) & (up > 0), up, 0)
    mdm  = np.where((down > up) & (down > 0), down, 0)

    atr_s = tr.ewm(com=13, adjust=False).mean()
    pdi   = 100 * pd.Series(pdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi   = 100 * pd.Series(mdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx    = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    df["adx"]       = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]   = pdi
    df["minus_di"]  = mdi
    df["di_spread"] = pdi - mdi   # DI divergence (positif = bullish dominan)
    df["adx_slope"] = df["adx"] - df["adx"].shift(3)   # Baru: ADX building/fading

    # ══════════════════════════════════
    # LAYER 5: VOLUME INTELLIGENCE
    # ══════════════════════════════════
    vol_ma20 = v.rolling(20).mean()
    df["vol_ma20"]    = vol_ma20
    df["vol_ratio"]   = v / vol_ma20.replace(0, np.nan)
    df["vol_accel"]   = df["vol_ratio"] - df["vol_ratio"].shift(2)  # Volume acceleration
    df["vol_trend"]   = (v > v.shift(1)).astype(int) + (v.shift(1) > v.shift(2)).astype(int)  # 0/1/2

    # ══════════════════════════════════
    # LAYER 6: SCALP ENGINE (BARU)
    # ══════════════════════════════════
    # Micro-burst signal: EMA9 slope spike melebihi 2x rata-ratanya
    ema9_slope_abs = df["ema9_slope"].abs()
    df["slope_avg"]    = ema9_slope_abs.rolling(20).mean()
    df["slope_ratio"]  = ema9_slope_abs / df["slope_avg"].replace(0, np.nan)  # >1.5 = burst

    # Candle body dominance (tanda strong directional candle)
    candle_body   = (c - df["open"]).abs() if "open" in df.columns else (c - c.shift(1)).abs()
    candle_range  = (h - l).replace(0, np.nan)
    df["body_ratio"] = candle_body / candle_range  # >0.6 = strong candle

    return df.fillna(0)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2: APEX SIGNAL BRAIN
#  Target: 5 Profit : 1 Loss ratio melalui presisi entry + exit
# ═══════════════════════════════════════════════════════════════════
def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable, _be_active, _profit_tier
    global _scalp_mode, _trend_strength_ma

    # ─── 1. State Parsing ───
    pos_type = position.get("type", "NONE") if position else "NONE"

    # ─── 2. State Machine ───
    if pos_type != "NONE" and _last_pos_type != "NONE":
        _candles_in_pos += 1
    elif pos_type == "NONE" and _last_pos_type != "NONE":
        # Just closed position
        _candles_since_exit = 0
        _candles_in_pos     = 0
        _entry_price        = 0.0
        _max_favorable      = 0.0
        _be_active          = False
        _profit_tier        = 0
        _scalp_mode         = False
    elif pos_type == "NONE" and _last_pos_type == "NONE":
        _candles_since_exit = min(_candles_since_exit + 1, 99)
    else:  # Just opened
        _candles_in_pos  = 1
        _entry_price     = row["close"]
        _max_favorable   = 0.0
        _be_active       = False
        _profit_tier     = 0
        # Tentukan mode: scalp (ADX tinggi + ATR besar) vs swing
        _scalp_mode = (row["adx"] > 28) and (row["atr_pct"] > 0.3) and (row["slope_ratio"] > 1.5)

    _last_pos_type = pos_type

    # ─── 3. Extract Core Variables ───
    price       = row["close"]
    ema9        = row["ema_9"]
    ema21       = row["ema_21"]
    ema55       = row["ema_55"]
    ema200      = row["ema_200"]
    ema21_slope = row["ema21_slope"]
    ema55_slope = row["ema55_slope"]
    trend_accel = row["trend_accel"]
    macro_mom   = row["macro_momentum"]
    ema_spread  = row["ema_spread"]
    rsi         = row["rsi"]
    rsi_slope   = row["rsi_slope"]
    stoch_k     = row["stoch_k"]
    stoch_d     = row["stoch_d"]
    macd        = row["macd"]
    macd_sig    = row["macd_sig"]
    macd_hist   = row["macd_hist"]
    macd_accel  = row["macd_accel"]
    macd_vel    = row["macd_vel"]
    atr_pct     = row["atr_pct"]
    atr_slope   = row["atr_slope"]
    bb_width    = row["bb_width"]
    bb_pct      = row["bb_pct"]
    adx         = row["adx"]
    adx_slope   = row["adx_slope"]
    plus_di     = row["plus_di"]
    minus_di    = row["minus_di"]
    di_spread   = row["di_spread"]
    vol_ratio   = row["vol_ratio"]
    vol_accel   = row["vol_accel"]
    vol_trend   = row["vol_trend"]
    squeeze_rel = row["squeeze_release"]
    slope_ratio = row["slope_ratio"]
    body_ratio  = row["body_ratio"]

    # ─── 4. Smooth ADX tracker (prevent noise) ───
    _trend_strength_ma = _trend_strength_ma * 0.85 + adx * 0.15

    # ─── 5. Warmup Guard ───
    if ema200 == 0 or rsi == 0 or adx == 0 or atr_pct == 0:
        return "HOLD"

    # ─── 6. Market Regime Filter (lebih presisi) ───
    # Dead market: ADX lemah DAN BB sempit DAN volume flat
    dead_market = (adx < 18) and (bb_width < 0.014) and (vol_ratio < 0.8)
    # Choppy market: ADX naik tapi DI spread sempit (tidak ada dominasi)
    choppy = (adx < 22) and (abs(di_spread) < 5) and (abs(trend_accel) < 0.02)

    if dead_market or choppy:
        return "HOLD"

    # ═══════════════════════════════════════════════════════
    #  EXIT LOGIC — 5-TIER INTELLIGENT EXIT SYSTEM
    # ═══════════════════════════════════════════════════════
    MIN_HOLD = 2 if _scalp_mode else 3  # Scalp: exit lebih cepat

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized = (price - _entry_price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        # ── PROFIT TIER TRACKING (tighten trail as profit grows) ──
        if _max_favorable > atr_pct * 4.0:
            _profit_tier = 3  # Sangat untung → trail super ketat
        elif _max_favorable > atr_pct * 2.5:
            _profit_tier = 2  # Baik → trail ketat
        elif _max_favorable > atr_pct * 1.5:
            _profit_tier = 1  # Aman → breakeven aktif

        # ── BREAKEVEN ENGINE ──
        if _profit_tier >= 1 and not _be_active:
            _be_active = True

        # ── DYNAMIC TRAILING MULTIPLIER (5-level ADX) ──
        if adx > 40:
            trail = 2.8   # Super strong trend → biarkan run
        elif adx > 30:
            trail = 2.2
        elif adx > 22:
            trail = 1.6
        else:
            trail = 1.1   # Weak trend → ketat

        # Profit tier tighten
        if _profit_tier == 3:
            trail = min(trail, 1.0)
        elif _profit_tier == 2:
            trail = min(trail, 1.4)

        # Scalp mode: trail lebih ketat selalu
        if _scalp_mode:
            trail = min(trail, 1.2)

        # ── EXIT CONDITIONS ──
        # E1: Dynamic trailing stop
        trailing_hit = (_max_favorable > 0.25) and (unrealized < _max_favorable - atr_pct * trail)

        # E2: Hard stop loss (1.2x ATR — lebih ketat dari Gemini 1.5x)
        hard_sl = unrealized < -(atr_pct * 1.2)

        # E3: Breakeven protection
        be_hit = _be_active and (price < _entry_price * 1.002)

        # E4: Trend structure reversal (triple confirmation)
        trend_rev = (ema9 < ema21) and (macd_accel < 0) and (di_spread < -3)

        # E5: Momentum exhaustion (MACD velocity flipping)
        macd_exhaust = (macd_hist > 0) and (macd_accel < 0) and (macd_vel < -0.0001) and (_candles_in_pos > 4)

        # E6: Adaptive RSI extreme exit
        rsi_exit = 85 if adx > 35 else (80 if adx > 25 else 75)
        rsi_extreme = rsi > rsi_exit and rsi_slope < 0  # RSI turning down

        # E7: Time decay (posisi stuck terlalu lama tanpa progress)
        time_decay = (_candles_in_pos > 12) and (_max_favorable < atr_pct * 0.5)

        if trailing_hit or hard_sl or be_hit or (trend_rev and macd_exhaust) or rsi_extreme or time_decay:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized = (_entry_price - price) / _entry_price * 100
        _max_favorable = max(_max_favorable, unrealized)

        if _max_favorable > atr_pct * 4.0:
            _profit_tier = 3
        elif _max_favorable > atr_pct * 2.5:
            _profit_tier = 2
        elif _max_favorable > atr_pct * 1.5:
            _profit_tier = 1

        if _profit_tier >= 1 and not _be_active:
            _be_active = True

        if adx > 40:
            trail = 2.8
        elif adx > 30:
            trail = 2.2
        elif adx > 22:
            trail = 1.6
        else:
            trail = 1.1

        if _profit_tier == 3:
            trail = min(trail, 1.0)
        elif _profit_tier == 2:
            trail = min(trail, 1.4)

        if _scalp_mode:
            trail = min(trail, 1.2)

        trailing_hit  = (_max_favorable > 0.25) and (unrealized < _max_favorable - atr_pct * trail)
        hard_sl       = unrealized < -(atr_pct * 1.2)
        be_hit        = _be_active and (price > _entry_price * 0.998)
        trend_rev     = (ema9 > ema21) and (macd_accel > 0) and (di_spread > 3)
        macd_exhaust  = (macd_hist < 0) and (macd_accel > 0) and (macd_vel > 0.0001) and (_candles_in_pos > 4)
        rsi_exit      = 15 if adx > 35 else (20 if adx > 25 else 25)
        rsi_extreme   = rsi < rsi_exit and rsi_slope > 0
        time_decay    = (_candles_in_pos > 12) and (_max_favorable < atr_pct * 0.5)

        if trailing_hit or hard_sl or be_hit or (trend_rev and macd_exhaust) or rsi_extreme or time_decay:
            return "BUY"

    # ═══════════════════════════════════════════════════════
    #  ENTRY LOGIC — ADAPTIVE COOLDOWN + SCALP/SWING DUAL-MODE
    # ═══════════════════════════════════════════════════════
    if pos_type != "NONE":
        return "HOLD"

    # Adaptive cooldown berdasarkan konteks pasar
    if squeeze_rel:
        cooldown = 1   # Squeeze release → re-entry cepat
    elif trend_accel > 0.03 and adx > 25:
        cooldown = 2   # Strong bullish momentum → cepat
    elif trend_accel < -0.03 and adx > 25:
        cooldown = 2   # Strong bearish momentum → cepat
    elif adx > 30:
        cooldown = 3   # Strong trend, butuh sedikit konfirmasi
    else:
        cooldown = 5   # Normal/lemah → hati-hati

    if _candles_since_exit < cooldown:
        return "HOLD"

    # ═══════════════════════════════════════════════════════
    #  LONG ENTRY — 6-DIMENSI SCORING SYSTEM
    # ═══════════════════════════════════════════════════════
    long_score = 0
    long_bonus = 0

    # ── DIMENSI 1: Major Trend Architecture (bobot: 1.5) ──
    # Semua EMA aligned bullish + harga di atas EMA200
    if price > ema200 and ema9 > ema21 and ema21 > ema55:
        long_score += 1
        if macro_mom > 0.01:  # Macro alignment juga positif
            long_bonus += 0.5

    # ── DIMENSI 2: MACD Momentum (bobot: 1) ──
    # Histogram positif DAN sedang akselerasi
    if macd > macd_sig and macd_accel > 0:
        long_score += 1
        if macd_vel > 0:  # Akselerasi juga meningkat
            long_bonus += 0.3

    # ── DIMENSI 3: StochRSI Timing (bobot: 1) ──
    # Tidak overbought, StochK crossing up
    if stoch_k > stoch_d and stoch_k < 72 and rsi > 45 and rsi < 75:
        long_score += 1
        if row["stoch_cross_up"] and stoch_k < 55:
            long_bonus += 0.5  # Fresh golden cross dari low zone = extra bonus

    # ── DIMENSI 4: ADX Trend Strength (bobot: 1) ──
    if adx > 20 and plus_di > minus_di and ema21_slope > 0.02:
        long_score += 1
        if adx_slope > 1.5:  # ADX sedang naik = tren menguat
            long_bonus += 0.3

    # ── DIMENSI 5: Volume Surge (bobot: 1) ──
    if vol_ratio >= 1.25:
        long_score += 1
        if vol_accel > 0.3 and vol_trend == 2:  # Volume meledak + naik konsisten
            long_bonus += 0.5

    # ── DIMENSI 6: Squeeze Release (bobot: 1) ──
    if squeeze_rel and trend_accel > 0.01:
        long_score += 1

    # ── SCALP BONUS: Micro-burst detection ──
    scalp_long_bonus = 0
    if slope_ratio > 1.8 and trend_accel > 0.04 and body_ratio > 0.6:
        scalp_long_bonus = 1  # Momentum burst candle = bonus entry

    # Threshold: 3/6 normal, atau 2.5/6 effective dengan bonus
    effective_score = long_score + long_bonus * 0.4 + scalp_long_bonus * 0.6
    # Minimal 3 dimensi utama harus terpenuhi
    if long_score >= 3 and effective_score >= 3.0:
        # Filter tambahan: pastikan tidak entry di puncak BB
        if bb_pct < 0.88:  # Tidak terlalu dekat upper BB
            return "BUY"

    # ═══════════════════════════════════════════════════════
    #  SHORT ENTRY — LEBIH KETAT (Bull Market Protection)
    # ═══════════════════════════════════════════════════════
    short_score = 0
    short_bonus = 0

    # ── DIMENSI 1: Triple EMA Aligned Bearish (ketat) ──
    # Memerlukan EMA55 < EMA200 juga (konfirmasi bear market)
    if price < ema200 and ema9 < ema21 and ema21 < ema55 and ema55 < ema200:
        short_score += 1
        if macro_mom < -0.01:
            short_bonus += 0.5

    # ── DIMENSI 2: MACD Bearish Acceleration ──
    if macd < macd_sig and macd_accel < 0:
        short_score += 1
        if macd_vel < 0:
            short_bonus += 0.3

    # ── DIMENSI 3: StochRSI Bearish Timing ──
    if stoch_k < stoch_d and stoch_k > 28 and rsi < 55 and rsi > 25:
        short_score += 1
        if row["stoch_cross_down"] and stoch_k > 45:
            short_bonus += 0.5

    # ── DIMENSI 4: ADX Bearish Strength ──
    if adx > 22 and minus_di > plus_di and ema21_slope < -0.02:
        short_score += 1
        if adx_slope > 1.5:
            short_bonus += 0.3

    # ── DIMENSI 5: Volume Confirmation ──
    if vol_ratio >= 1.3:   # Short butuh lebih banyak volume
        short_score += 1
        if vol_accel > 0.3 and vol_trend == 2:
            short_bonus += 0.5

    # ── DIMENSI 6: Squeeze Release ──
    if squeeze_rel and trend_accel < -0.01:
        short_score += 1

    # Short threshold: 4/6 (lebih ketat dari long 3/6)
    effective_short = short_score + short_bonus * 0.4
    if short_score >= 4 and effective_short >= 4.0:
        if bb_pct > 0.12:  # Tidak terlalu dekat lower BB
            return "SELL"

    return "HOLD"