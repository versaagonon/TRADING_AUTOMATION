def calculate_indicators(df, ta):
    # Triple EMA + MACD (Profesional v10.0)
    df['EMA_9'] = ta.ema(df['close'], length=9)
    df['EMA_21'] = ta.ema(df['close'], length=21)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    
    macd = ta.macd(df['close'], fast=12, slow=26, signal=9)
    df['MACDh'] = macd['MACDh_12_26_9']
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    return df

def get_signal(row, position):
    ema9 = row['EMA_9']
    ema21 = row['EMA_21']
    ema50 = row['EMA_50']
    macdh = row['MACDh']
    rsi = row['RSI_14']
    
    # Logic LONG (Trend Up)
    if not position or position['type'] == 'SHORT':
        if (ema9 > ema21 > ema50) and (macdh > 0) and (rsi > 45):
            return "BUY"
            
    # Logic SHORT (Trend Down)
    if not position or position['type'] == 'LONG':
        if (ema9 < ema21 < ema50) and (macdh < 0) and (rsi < 55):
            return "SELL"
            
    return "HOLD"
