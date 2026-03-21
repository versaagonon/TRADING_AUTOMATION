import pandas as pd
import numpy as np

# ─────────────────────────────────────────────
#  STATE TRACKING UNTUK ENGINE 411
# ─────────────────────────────────────────────
candles_in_position = 0
candles_since_last_exit = 99
last_pos_type = "NONE"

# ─────────────────────────────────────────────
#  SECTION 1: CALCULATE INDICATORS v2
# ─────────────────────────────────────────────
def calculate_indicators(df: pd.DataFrame, ta=None) -> pd.DataFrame:
    df = df.copy()
    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # ── EMA Trend ────────────────────────────────────────────────
    df["ema_21"]  = close.ewm(span=21,  adjust=False).mean()
    df["ema_50"]  = close.ewm(span=50,  adjust=False).mean()
    df["ema_200"] = close.ewm(span=200, adjust=False).mean()

    # [NEW v2] EMA Slope
    df["ema21_slope"] = (df["ema_21"] - df["ema_21"].shift(3)) / df["ema_21"].replace(0, np.nan) * 100
    df["ema50_slope"] = (df["ema_50"] - df["ema_50"].shift(3)) / df["ema_50"].replace(0, np.nan) * 100

    # ── RSI 14 ────────────────────────────────────────────────────
    delta     = close.diff()
    gain      = delta.clip(lower=0)
    loss      = -delta.clip(upper=0)
    avg_gain  = gain.ewm(com=13, adjust=False).mean()
    avg_loss  = loss.ewm(com=13, adjust=False).mean()
    rs        = avg_gain / avg_loss.replace(0, np.nan)
    df["rsi"] = 100 - (100 / (1 + rs))

    # ── MACD ──────────────────────────────────────────────────────
    ema_12          = close.ewm(span=12, adjust=False).mean()
    ema_26          = close.ewm(span=26, adjust=False).mean()
    df["macd"]      = ema_12 - ema_26
    df["macd_sig"]  = df["macd"].ewm(span=9, adjust=False).mean()
    df["macd_hist"] = df["macd"] - df["macd_sig"]

    df["macd_rising"]  = (df["macd_hist"] > df["macd_hist"].shift(1)) & (df["macd_hist"].shift(1) > df["macd_hist"].shift(2))
    df["macd_falling"] = (df["macd_hist"] < df["macd_hist"].shift(1)) & (df["macd_hist"].shift(1) < df["macd_hist"].shift(2))

    # ── Bollinger Bands ───────────────────────────────────────────
    bb_mid          = close.rolling(20).mean()
    bb_std          = close.rolling(20).std()
    df["bb_upper"]  = bb_mid + 2 * bb_std
    df["bb_lower"]  = bb_mid - 2 * bb_std
    df["bb_width"]  = (df["bb_upper"] - df["bb_lower"]) / bb_mid.replace(0, np.nan)

    # ── ATR 14 ───────────────────────────────────────────────────
    prev_close   = close.shift(1)
    tr           = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low  - prev_close).abs()
    ], axis=1).max(axis=1)
    df["atr"]     = tr.ewm(com=13, adjust=False).mean()
    df["atr_pct"] = df["atr"] / close.replace(0, np.nan) * 100

    # ── ADX 14 ───────────────────────────────────────────────────
    up_move   = high - high.shift(1)
    down_move = low.shift(1) - low
    plus_dm   = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm  = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

    atr_raw    = tr.ewm(com=13, adjust=False).mean()
    plus_di    = 100 * pd.Series(plus_dm, index=df.index).ewm(com=13, adjust=False).mean() / atr_raw.replace(0, np.nan)
    minus_di   = 100 * pd.Series(minus_dm, index=df.index).ewm(com=13, adjust=False).mean() / atr_raw.replace(0, np.nan)

    dx              = (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, np.nan)) * 100
    df["adx"]       = dx.ewm(com=13, adjust=False).mean()
    df["plus_di"]   = plus_di
    df["minus_di"]  = minus_di

    # ── Volume ───────────────────────────────────────────────────
    df["vol_ma20"]  = vol.rolling(20).mean()
    df["vol_ratio"] = vol / df["vol_ma20"].replace(0, np.nan)

    # Isi NaN dengan 0 untuk keamanan Engine
    return df.fillna(0)

# ─────────────────────────────────────────────
#  SECTION 2: SIGNAL LOGIC v2 (Engine 411 Format)
# ─────────────────────────────────────────────
def get_signal(row: pd.Series, position=None) -> str:
    global candles_in_position, candles_since_last_exit, last_pos_type

    # 1. State Parsing
    pos_type = position.get("type", "NONE") if position else "NONE"

    # 2. Update Internal Counters
    if pos_type != "NONE" and last_pos_type != "NONE":
        candles_in_position += 1
    elif pos_type == "NONE" and last_pos_type != "NONE":
        # Just Exited
        candles_since_last_exit = 0
        candles_in_position = 0
    elif pos_type == "NONE" and last_pos_type == "NONE":
        candles_since_last_exit = min(candles_since_last_exit + 1, 99)
    elif pos_type != "NONE" and last_pos_type == "NONE":
        # Just Entered
        candles_in_position = 1

    last_pos_type = pos_type

    # 3. Extract Row Variables
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

    # 4. Gate Checks
    if adx < 18 or bb_width < 0.015 or atr_pct < 0.25:
        return "HOLD"
    
    if ema21 == 0 or rsi == 0 or macd == 0:
        return "HOLD" # Warmup

    # 5. Exit Logic (Minimum Hold)
    MIN_HOLD_CANDLES = 4
    if pos_type == "LONG" and candles_in_position >= MIN_HOLD_CANDLES:
        trend_reversal = (ema21 < ema50) and (macd < macd_sig)
        rsi_overbought = rsi > 78
        di_reversal    = minus_di > plus_di and adx > 20
        adx_weakening  = adx < 18

        if (trend_reversal and di_reversal) or rsi_overbought or adx_weakening:
            return "SELL"

    if pos_type == "SHORT" and candles_in_position >= MIN_HOLD_CANDLES:
        trend_reversal = (ema21 > ema50) and (macd > macd_sig)
        rsi_oversold   = rsi < 22
        di_reversal    = plus_di > minus_di and adx > 20
        adx_weakening  = adx < 18

        if (trend_reversal and di_reversal) or rsi_oversold or adx_weakening:
            return "BUY"

    # 6. Entry Logic (Cooldown & Threshold)
    COOLDOWN_CANDLES = 6
    if pos_type == "NONE" and candles_since_last_exit < COOLDOWN_CANDLES:
        return "HOLD"

    if pos_type == "NONE":
        # LONG check
        long_signals = 0
        if price > ema200 and plus_di > minus_di: long_signals += 1
        if ema21 > ema50 and ema21_slope > 0.05: long_signals += 1
        if 42 <= rsi <= 60: long_signals += 1
        if macd > macd_sig and macd_rising: long_signals += 1
        if vol_ratio >= 1.5 and adx >= 22: long_signals += 1
        
        if long_signals >= 4:
            return "BUY"

        # SHORT check
        short_signals = 0
        if price < ema200 and minus_di > plus_di: short_signals += 1
        if ema21 < ema50 and ema21_slope < -0.05: short_signals += 1
        if 40 <= rsi <= 58: short_signals += 1
        if macd < macd_sig and macd_falling: short_signals += 1
        if vol_ratio >= 1.5 and adx >= 22: short_signals += 1
        
        if short_signals >= 4:
            return "SELL"

    return "HOLD"
