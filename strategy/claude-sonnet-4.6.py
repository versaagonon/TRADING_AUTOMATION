import pandas as pd
import numpy as np

# ═══════════════════════════════════════════════════════════════════
#  CLAUDE OPUS 4.6 v2 — "ADAPTIVE MOMENTUM HUNTER II"
# ═══════════════════════════════════════════════════════════════════
#  Berdasarkan kemenangan OPUS v1 (+92.04%) di kualifikasi
#  Target v2: 120–160%+ ROI
#
#  DIPERTAHANKAN dari v1 (faktor kemenangan):
#  ✓ Stochastic RSI timing
#  ✓ ATR Trailing Stop (biarkan profit berlari)
#  ✓ EMA 9/21/55/200 quad-trend filter
#  ✓ Threshold 3/5 (tidak over-filter)
#  ✓ Trend Acceleration detector
#
#  IMPROVEMENT v2:
#  + Weighted scoring: kondisi kuat = 2 poin, lemah = 1 poin
#  + Trailing stop lebih ketat saat profit besar (protect gains)
#  + Volume momentum: cek apakah volume trend mendukung
#  + EMA55 slope sebagai konfirmasi mid-trend
#  + StochRSI zone diperluas untuk lebih banyak entry
#  + Market regime: bull/bear/neutral — logic berbeda per regime
# ═══════════════════════════════════════════════════════════════════

# ─── INTERNAL STATE ───
_candles_in_pos     = 0
_candles_since_exit = 99
_last_pos_type      = "NONE"
_entry_price        = 0.0
_max_favorable      = 0.0


# ═══════════════════════════════════════════════════════════════════
#  SECTION 1: INDICATOR ENGINE v2
# ═══════════════════════════════════════════════════════════════════
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    c  = df["close"]
    h  = df["high"]
    l  = df["low"]
    v  = df["volume"]

    # ═══ LAYER 1: TREND STRUCTURE (4-level EMA) ═══
    df["ema_9"]   = c.ewm(span=9,   adjust=False).mean()
    df["ema_21"]  = c.ewm(span=21,  adjust=False).mean()
    df["ema_55"]  = c.ewm(span=55,  adjust=False).mean()
    df["ema_200"] = c.ewm(span=200, adjust=False).mean()

    # Slope indicators (trend speed & direction)
    df["ema9_slope"]  = (df["ema_9"]  - df["ema_9"].shift(2))  / df["ema_9"].replace(0, np.nan)  * 100
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["ema55_slope"] = (df["ema_55"] - df["ema_55"].shift(5)) / df["ema_55"].replace(0, np.nan) * 100

    # Trend Acceleration (ema9 vs ema21 slope diff)
    df["trend_accel"] = df["ema9_slope"] - df["ema21_slope"]

    # EMA alignment score: berapa banyak EMA yang tersusun bullish
    df["ema_bull_count"] = (
        (df["ema_9"]  > df["ema_21"]).astype(int) +
        (df["ema_21"] > df["ema_55"]).astype(int) +
        (df["ema_55"] > df["ema_200"]).astype(int)
    )
    df["ema_bear_count"] = (
        (df["ema_9"]  < df["ema_21"]).astype(int) +
        (df["ema_21"] < df["ema_55"]).astype(int) +
        (df["ema_55"] < df["ema_200"]).astype(int)
    )

    # ═══ LAYER 2: MOMENTUM ═══
    # RSI 14
    delta = c.diff()
    gain  = delta.clip(lower=0)
    loss  = -delta.clip(upper=0)
    ag    = gain.ewm(com=13, adjust=False).mean()
    al    = loss.ewm(com=13, adjust=False).mean()
    rs    = ag / al.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # RSI Slope (apakah momentum sedang naik atau turun)
    df["rsi_slope"] = df["rsi"] - df["rsi"].shift(3)

    # Stochastic RSI — presisi timing entry/exit
    rsi_min       = df["rsi"].rolling(14).min()
    rsi_max       = df["rsi"].rolling(14).max()
    rsi_range     = (rsi_max - rsi_min).replace(0, np.nan)
    stoch_k_raw   = ((df["rsi"] - rsi_min) / rsi_range) * 100
    df["stoch_k"] = stoch_k_raw.rolling(3).mean()
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Stochastic crossover
    df["stoch_bull_cross"] = (
        (df["stoch_k"] > df["stoch_d"]) &
        (df["stoch_k"].shift(1) <= df["stoch_d"].shift(1))
    ).astype(int)
    df["stoch_bear_cross"] = (
        (df["stoch_k"] < df["stoch_d"]) &
        (df["stoch_k"].shift(1) >= df["stoch_d"].shift(1))
    ).astype(int)

    # MACD 12/26/9
    ema12           = c.ewm(span=12, adjust=False).mean()
    ema26           = c.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema12 - ema26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]
    df["macd_accel"] = df["macd_hist"] - df["macd_hist"].shift(1)

    # MACD histogram trend (2 candle naik/turun berturut)
    df["macd_rising"]  = (
        (df["macd_hist"] > df["macd_hist"].shift(1)) &
        (df["macd_hist"].shift(1) > df["macd_hist"].shift(2))
    ).astype(int)
    df["macd_falling"] = (
        (df["macd_hist"] < df["macd_hist"].shift(1)) &
        (df["macd_hist"].shift(1) < df["macd_hist"].shift(2))
    ).astype(int)

    # ═══ LAYER 3: VOLATILITY ═══
    prev_c = c.shift(1)
    tr     = pd.concat([
        h - l,
        (h - prev_c).abs(),
        (l - prev_c).abs()
    ], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / c.replace(0, np.nan) * 100

    # Bollinger Bands
    bb_mid         = c.rolling(20).mean()
    bb_std         = c.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # BB position (0 = di lower, 1 = di upper)
    bb_range       = (df["bb_upper"] - df["bb_lower"]).replace(0, np.nan)
    df["bb_pos"]   = (c - df["bb_lower"]) / bb_range

    # ═══ LAYER 4: TREND STRENGTH (ADX) ═══
    up   = h - h.shift(1)
    down = l.shift(1) - l
    pdm  = np.where((up > down) & (up > 0), up, 0.0)
    mdm  = np.where((down > up) & (down > 0), down, 0.0)
    atr_s = tr.ewm(com=13, adjust=False).mean()
    pdi  = 100 * pd.Series(pdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    mdi  = 100 * pd.Series(mdm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx   = (abs(pdi - mdi) / (pdi + mdi).replace(0, np.nan)) * 100
    df["adx"]      = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]  = pdi
    df["minus_di"] = mdi
    df["di_diff"]  = pdi - mdi  # positif = bullish pressure

    # ═══ LAYER 5: VOLUME INTELLIGENCE ═══
    df["vol_ma20"]     = v.rolling(20).mean()
    df["vol_ratio"]    = v / df["vol_ma20"].replace(0, np.nan)
    df["vol_ma5"]      = v.rolling(5).mean()
    # Volume momentum: apakah short-term volume > long-term volume
    df["vol_momentum"] = df["vol_ma5"] / df["vol_ma20"].replace(0, np.nan)

    return df.fillna(0)


# ═══════════════════════════════════════════════════════════════════
#  SECTION 2: SIGNAL BRAIN v2
# ═══════════════════════════════════════════════════════════════════
def get_signal(row: pd.Series, position=None) -> str:
    global _candles_in_pos, _candles_since_exit, _last_pos_type
    global _entry_price, _max_favorable

    # ─── 1. State Parsing ───────────────────────────────────────
    pos_type = position.get("type", "NONE") if position else "NONE"

    # ─── 2. State Machine ────────────────────────────────────────
    if pos_type != "NONE" and _last_pos_type != "NONE":
        _candles_in_pos += 1
    elif pos_type == "NONE" and _last_pos_type != "NONE":
        _candles_since_exit = 0
        _candles_in_pos     = 0
        _entry_price        = 0.0
        _max_favorable      = 0.0
    elif pos_type == "NONE" and _last_pos_type == "NONE":
        _candles_since_exit = min(_candles_since_exit + 1, 99)
    else:  # baru masuk posisi
        _candles_in_pos = 1
        _entry_price    = float(row["close"])
        _max_favorable  = 0.0

    _last_pos_type = pos_type

    # ─── 3. Extract Variables ────────────────────────────────────
    price         = float(row["close"])
    ema9          = float(row["ema_9"])
    ema21         = float(row["ema_21"])
    ema55         = float(row["ema_55"])
    ema200        = float(row["ema_200"])
    ema21_slope   = float(row["ema21_slope"])
    ema55_slope   = float(row["ema55_slope"])
    trend_accel   = float(row["trend_accel"])
    ema_bull      = int(row["ema_bull_count"])
    ema_bear      = int(row["ema_bear_count"])
    rsi           = float(row["rsi"])
    rsi_slope     = float(row["rsi_slope"])
    stoch_k       = float(row["stoch_k"])
    stoch_d       = float(row["stoch_d"])
    stoch_bull_x  = bool(row["stoch_bull_cross"])
    stoch_bear_x  = bool(row["stoch_bear_cross"])
    macd          = float(row["macd"])
    macd_sig      = float(row["macd_sig"])
    macd_hist     = float(row["macd_hist"])
    macd_accel    = float(row["macd_accel"])
    macd_rising   = bool(row["macd_rising"])
    macd_falling  = bool(row["macd_falling"])
    atr_pct       = float(row["atr_pct"])
    bb_width      = float(row["bb_width"])
    bb_pos        = float(row["bb_pos"])
    adx           = float(row["adx"])
    plus_di       = float(row["plus_di"])
    minus_di      = float(row["minus_di"])
    di_diff       = float(row["di_diff"])
    vol_ratio     = float(row["vol_ratio"])
    vol_momentum  = float(row["vol_momentum"])

    # ─── 4. Warmup Guard ─────────────────────────────────────────
    if ema200 == 0 or rsi == 0 or adx == 0:
        return "HOLD"

    # ─── 5. Market Regime Filter ─────────────────────────────────
    # Hanya skip saat market benar-benar mati (ADX sangat lemah
    # DAN BB squeeze) — tidak terlalu agresif filter
    if adx < 15 and bb_width < 0.010:
        return "HOLD"

    # ─── 6. Determine Market Regime ──────────────────────────────
    # Bull: price di atas ema200 + ema aligned bullish
    # Bear: price di bawah ema200 + ema aligned bearish
    # Neutral: mixed
    if price > ema200 and ema_bull >= 2:
        regime = "BULL"
    elif price < ema200 and ema_bear >= 2:
        regime = "BEAR"
    else:
        regime = "NEUTRAL"

    # ═══════════════════════════════════════════════════
    # 7. EXIT LOGIC — ATR Trailing + Structure Breakdown
    # ═══════════════════════════════════════════════════
    MIN_HOLD = 3

    if pos_type == "LONG" and _candles_in_pos >= MIN_HOLD:
        unrealized     = (price - _entry_price) / max(_entry_price, 1) * 100
        _max_favorable = max(_max_favorable, unrealized)

        # Trailing stop — semakin besar profit, semakin ketat trailing
        if _max_favorable > 3.0:
            trail_mult = 1.0    # profit besar: trail ketat (1.0× ATR)
        elif _max_favorable > 1.5:
            trail_mult = 1.3    # profit sedang: trail normal
        else:
            trail_mult = 1.8    # profit kecil: ruang lebih besar

        trailing_hit = (
            unrealized < (_max_favorable - atr_pct * trail_mult)
            and _max_favorable > 0.25
        )

        # Trend breakdown: ema9 < ema21 + macd berbalik + momentum negatif
        trend_broken = (ema9 < ema21) and (macd < macd_sig) and (macd_accel < 0)

        # RSI extreme overbought
        rsi_ob = rsi > 78

        # DI bearish takeover yang kuat
        di_bear = (minus_di > plus_di + 8) and (adx > 18)

        # StochRSI bearish cross dari overbought
        stoch_exit = stoch_bear_x and stoch_k > 65

        if trailing_hit or rsi_ob or (trend_broken and di_bear) or stoch_exit:
            return "SELL"

    if pos_type == "SHORT" and _candles_in_pos >= MIN_HOLD:
        unrealized     = (_entry_price - price) / max(_entry_price, 1) * 100
        _max_favorable = max(_max_favorable, unrealized)

        if _max_favorable > 3.0:
            trail_mult = 1.0
        elif _max_favorable > 1.5:
            trail_mult = 1.3
        else:
            trail_mult = 1.8

        trailing_hit = (
            unrealized < (_max_favorable - atr_pct * trail_mult)
            and _max_favorable > 0.25
        )

        trend_broken = (ema9 > ema21) and (macd > macd_sig) and (macd_accel > 0)
        rsi_os       = rsi < 22
        di_bull      = (plus_di > minus_di + 8) and (adx > 18)
        stoch_exit   = stoch_bull_x and stoch_k < 35

        if trailing_hit or rsi_os or (trend_broken and di_bull) or stoch_exit:
            return "BUY"

    # ═══════════════════════════════════════════════════
    # 8. ENTRY LOGIC — Weighted Confluence Scoring
    # ═══════════════════════════════════════════════════
    COOLDOWN = 4

    if pos_type != "NONE":
        return "HOLD"
    if _candles_since_exit < COOLDOWN:
        return "HOLD"

    # ── LONG ENTRY — Weighted Score System ──────────────────────
    # Tier A (bobot 2): kondisi paling prediktif berdasarkan v1
    # Tier B (bobot 1): konfirmasi tambahan
    long_score = 0

    # [TIER A — bobot 2 poin]
    # Dari analisis v1: EMA200 + alignment adalah faktor dominan
    if price > ema200 and ema_bull >= 2:
        long_score += 2  # Major trend bullish

    # StochRSI timing — paling membedakan Opus dari strategi lain
    if stoch_k > stoch_d and stoch_k < 72 and rsi > 42:
        long_score += 2  # Momentum timing tepat

    # [TIER B — bobot 1 poin]
    if macd > macd_sig and (macd_accel > 0 or macd_rising):
        long_score += 1  # MACD mendukung

    if adx > 20 and plus_di > minus_di:
        long_score += 1  # Trend strength bullish

    if ema21_slope > 0.02 and ema55_slope > 0.01:
        long_score += 1  # Dual slope konfirmasi (mid + long term naik)

    if vol_ratio >= 1.2 or vol_momentum >= 1.1:
        long_score += 1  # Volume mendukung

    # [REGIME BONUS]
    if regime == "BULL" and trend_accel > 0:
        long_score += 1  # Di bull market + accelerating = kuat

    # Threshold: 5 poin dari max ~9
    # (cukup selektif tapi tidak over-filter)
    if long_score >= 5:
        return "BUY"

    # ── SHORT ENTRY — Mirror dari LONG ──────────────────────────
    short_score = 0

    if price < ema200 and ema_bear >= 2:
        short_score += 2

    if stoch_k < stoch_d and stoch_k > 28 and rsi < 58:
        short_score += 2

    if macd < macd_sig and (macd_accel < 0 or macd_falling):
        short_score += 1

    if adx > 20 and minus_di > plus_di:
        short_score += 1

    if ema21_slope < -0.02 and ema55_slope < -0.01:
        short_score += 1

    if vol_ratio >= 1.2 or vol_momentum >= 1.1:
        short_score += 1

    if regime == "BEAR" and trend_accel < 0:
        short_score += 1

    if short_score >= 5:
        return "SELL"

    return "HOLD"