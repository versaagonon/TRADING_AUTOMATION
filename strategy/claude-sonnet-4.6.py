import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
#  STATE TRACKING UNTUK ENGINE 411
# ─────────────────────────────────────────────
candles_in_position     = 0
candles_since_last_exit = 99
last_pos_type           = "NONE"

# ─────────────────────────────────────────────
#  SECTION 1: CALCULATE INDICATORS v3
#  Fix: parameter lebih longgar, ADX tetap ada
#  tapi threshold entry lebih realistis (3/5+ADX)
# ─────────────────────────────────────────────
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df    = df.copy()
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # ── EMA Trend ─────────────────────────────────────────────────
    df["ema_21"]  = close.ewm(span=21,  adjust=False).mean()
    df["ema_50"]  = close.ewm(span=50,  adjust=False).mean()
    df["ema_200"] = close.ewm(span=200, adjust=False).mean()

    # EMA Slope (3 candle lookback)
    df["ema21_slope"] = (
        (df["ema_21"] - df["ema_21"].shift(3))
        / df["ema_21"].replace(0, np.nan) * 100
    )

    # ── RSI 14 ────────────────────────────────────────────────────
    delta    = close.diff()
    gain     = delta.clip(lower=0)
    loss     = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=13, adjust=False).mean()
    avg_loss = loss.ewm(com=13, adjust=False).mean()
    rs       = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # ── MACD ──────────────────────────────────────────────────────
    ema_12          = close.ewm(span=12, adjust=False).mean()
    ema_26          = close.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema_12 - ema_26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]

    # MACD histogram direction (1 candle konfirmasi — lebih sensitif dari v2)
    df["macd_rising"]  = df["macd_hist"] > df["macd_hist"].shift(1)
    df["macd_falling"] = df["macd_hist"] < df["macd_hist"].shift(1)

    # ── Bollinger Bands ───────────────────────────────────────────
    bb_mid         = close.rolling(20).mean()
    bb_std         = close.rolling(20).std()
    df["bb_upper"] = bb_mid + 2 * bb_std
    df["bb_lower"] = bb_mid - 2 * bb_std
    df["bb_width"] = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # ── ATR 14 ────────────────────────────────────────────────────
    prev_close    = close.shift(1)
    tr            = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / close.replace(0, np.nan) * 100

    # ── ADX 14 (kunci anti-ranging) ───────────────────────────────
    up_move  = high - high.shift(1)
    dn_move  = low.shift(1) - low
    plus_dm  = np.where((up_move > dn_move)  & (up_move > 0), up_move, 0.0)
    minus_dm = np.where((dn_move  > up_move) & (dn_move  > 0), dn_move, 0.0)

    atr_s    = tr.ewm(com=13, adjust=False).mean()
    plus_di  = 100 * pd.Series(plus_dm,  index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    minus_di = 100 * pd.Series(minus_dm, index=df.index).ewm(com=13, adjust=False).mean() / atr_s.replace(0, np.nan)
    dx       = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100

    df["adx"]      = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]  = plus_di
    df["minus_di"] = minus_di

    # ── Volume ────────────────────────────────────────────────────
    df["vol_ma20"]  = vol.rolling(20).mean()
    df["vol_ratio"] = vol / df["vol_ma20"].replace(0, np.nan)

    return df.fillna(0)


# ─────────────────────────────────────────────
#  SECTION 2: SIGNAL LOGIC v3
#
#  Filosofi v3:
#   - ADX wajib > 20 (cukup ketat, tidak over-filter)
#   - Threshold 3/5 TAPI ADX + DI wajib masuk hitungan
#   - Cooldown 3 candle (bukan 6) — crypto bergerak cepat
#   - Min hold 2 candle (bukan 4) — exit lebih fleksibel
#   - Exit 1 kondisi OR (bukan AND) — tidak terlambat keluar
# ─────────────────────────────────────────────
def get_signal(row: pd.Series, position=None) -> str:
    global candles_in_position, candles_since_last_exit, last_pos_type

    # ── 1. State Parsing ─────────────────────────────────────────
    pos_type = position.get("type", "NONE") if position else "NONE"

    # ── 2. Update Internal Counters ──────────────────────────────
    if pos_type != "NONE" and last_pos_type != "NONE":
        candles_in_position += 1
    elif pos_type == "NONE" and last_pos_type != "NONE":
        candles_since_last_exit = 0
        candles_in_position     = 0
    elif pos_type == "NONE" and last_pos_type == "NONE":
        candles_since_last_exit = min(candles_since_last_exit + 1, 99)
    elif pos_type != "NONE" and last_pos_type == "NONE":
        candles_in_position = 1

    last_pos_type = pos_type

    # ── 3. Extract Row Variables ──────────────────────────────────
    price        = row["close"]
    ema21        = row["ema_21"]
    ema50        = row["ema_50"]
    ema200       = row["ema_200"]
    ema21_slope  = row["ema21_slope"]
    rsi          = row["rsi"]
    macd         = row["macd"]
    macd_sig     = row["macd_sig"]
    macd_rising  = row["macd_rising"]
    macd_falling = row["macd_falling"]
    bb_width     = row["bb_width"]
    atr_pct      = row["atr_pct"]
    adx          = row["adx"]
    plus_di      = row["plus_di"]
    minus_di     = row["minus_di"]
    vol_ratio    = row["vol_ratio"]

    # ── 4. Hard Gate (wajib lulus, tapi lebih longgar dari v2) ───
    # ADX > 20: cukup untuk pastikan ada trend
    # BB width > 0.01: hanya block squeeze ekstrem
    # ATR > 0.15%: hanya block candle mati total
    if adx < 20 or bb_width < 0.01 or atr_pct < 0.15:
        return "HOLD"

    # Warmup check
    if ema21 == 0 or rsi == 0:
        return "HOLD"

    # ── 5. EXIT Logic (Min Hold: 2 candle, bukan 4) ──────────────
    MIN_HOLD = 2

    if pos_type == "LONG" and candles_in_position >= MIN_HOLD:
        # Exit jika SALAH SATU kondisi terpenuhi (OR — lebih responsif)
        trend_flip = (ema21 < ema50) and (macd < macd_sig)
        rsi_ob     = rsi > 75
        di_flip    = (minus_di > plus_di) and (minus_di - plus_di > 5)
        adx_dead   = adx < 16

        if trend_flip or rsi_ob or di_flip or adx_dead:
            return "SELL"

    if pos_type == "SHORT" and candles_in_position >= MIN_HOLD:
        trend_flip = (ema21 > ema50) and (macd > macd_sig)
        rsi_os     = rsi < 25
        di_flip    = (plus_di > minus_di) and (plus_di - minus_di > 5)
        adx_dead   = adx < 16

        if trend_flip or rsi_os or di_flip or adx_dead:
            return "BUY"

    # ── 6. ENTRY Logic (Cooldown: 3 candle) ──────────────────────
    COOLDOWN = 3

    if pos_type != "NONE":
        return "HOLD"

    if candles_since_last_exit < COOLDOWN:
        return "HOLD"

    # ── LONG Entry: 3/5, tapi [1] ADX/DI WAJIB masuk ────────────
    long_score = 0

    # [WAJIB] ADX kuat + DI bullish
    if adx >= 20 and plus_di > minus_di:
        long_score += 1
    else:
        return "HOLD"   # jika DI tidak bullish, langsung skip long

    # [2] Macro trend
    if price > ema200:
        long_score += 1

    # [3] EMA alignment + slope naik
    if ema21 > ema50 and ema21_slope > 0.03:
        long_score += 1

    # [4] RSI momentum sehat (lebih lebar dari v2: 40–63)
    if 40 <= rsi <= 63:
        long_score += 1

    # [5] MACD bullish + histogram naik
    if macd > macd_sig and macd_rising:
        long_score += 1

    # [BONUS] Volume spike (tidak diwajibkan tapi boosts score)
    if vol_ratio >= 1.3:
        long_score += 0.5

    if long_score >= 3:
        return "BUY"

    # ── SHORT Entry: mirror dari LONG ────────────────────────────
    short_score = 0

    # [WAJIB] ADX kuat + DI bearish
    if adx >= 20 and minus_di > plus_di:
        short_score += 1
    else:
        return "HOLD"

    # [2] Macro trend
    if price < ema200:
        short_score += 1

    # [3] EMA alignment + slope turun
    if ema21 < ema50 and ema21_slope < -0.03:
        short_score += 1

    # [4] RSI momentum bearish (38–62)
    if 38 <= rsi <= 62:
        short_score += 1

    # [5] MACD bearish + histogram turun
    if macd < macd_sig and macd_falling:
        short_score += 1

    # [BONUS] Volume spike
    if vol_ratio >= 1.3:
        short_score += 0.5

    if short_score >= 3:
        return "SELL"

    return "HOLD"