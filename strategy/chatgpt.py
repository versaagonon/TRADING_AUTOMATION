import pandas as pd
import pandas_ta as ta

def calculate_indicators(df, ta_lib=None):
    if ta_lib is None: import pandas_ta as ta_lib
    df = df.copy()
    # Trend indikator: EMA jangka pendek dan panjang
    df['EMA20'] = ta_lib.ema(df['close'], length=20)
    df['EMA50'] = ta_lib.ema(df['close'], length=50)
    # Momentum indikator: RSI dan MACD
    df['RSI']    = ta_lib.rsi(df['close'], length=14)
    macd = ta_lib.macd(df['close'], fast=12, slow=26, signal=9)
    if macd is not None:
        df['MACD_Line']   = macd.iloc[:, 0]
        df['MACD_Signal'] = macd.iloc[:, 1]
        df['MACD_Hist']   = macd.iloc[:, 2]
    else:
        df['MACD_Line'] = df['MACD_Signal'] = df['MACD_Hist'] = 0
    # Volatilitas indikator: Bollinger Bands dan ATR
    bb = ta_lib.bbands(df['close'], length=20, std=2)
    if bb is not None:
        df['BB_upper'] = bb.iloc[:, 2]
        df['BB_lower'] = bb.iloc[:, 0]
    else:
        df['BB_upper'] = df['BB_lower'] = df['close']
    df['ATR'] = ta_lib.atr(df['high'], df['low'], df['close'], length=14)
    return df.fillna(0)

def get_signal(row, position):
    signal = "HOLD"
    
    is_none  = not position
    is_long  = position and position.get('type') == 'LONG'
    is_short = position and position.get('type') == 'SHORT'
    
    # ── KONDISI LONG ──
    cond_long_entry = (
        (row['EMA20'] > row['EMA50']) and 
        (row['RSI'] < 40) and 
        (row['close'] <= row['BB_lower'])
    )
    cond_long_exit = (
        (row['RSI'] > 70) or 
        (row['close'] >= row['BB_upper']) or 
        (row['MACD_Hist'] < 0)
    )

    # ── KONDISI SHORT ──
    cond_short_entry = (
        (row['EMA20'] < row['EMA50']) and 
        (row['RSI'] > 60) and 
        (row['close'] >= row['BB_upper'])
    )
    cond_short_exit = (
        (row['RSI'] < 30) or 
        (row['close'] <= row['BB_lower']) or 
        (row['MACD_Hist'] > 0)
    )
    
    # ── MESIN EKSEKUSI ──
    if is_none:
        if cond_long_entry:
            signal = "BUY"
        elif cond_short_entry:
            signal = "SELL"
    elif is_long:
        if cond_long_exit:
            signal = "SELL"
    elif is_short:
        if cond_short_exit:
            signal = "BUY"
            
    return signal
