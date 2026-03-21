def calculate_indicators(df, ta):
    # 1. Trend Filter Mayor (Untuk melihat arah tren jangka panjang)
    df['EMA_200'] = ta.ema(df['close'], length=200)
    
    # 2. Fast & Slow EMA (Tetap menggunakan standar MACD)
    df['EMA_12'] = ta.ema(df['close'], length=12)
    df['EMA_26'] = ta.ema(df['close'], length=26)
    
    # 3. Momentum (Menggunakan RSI 14 agar lebih stabil, bukan RSI 9)
    df['RSI_14'] = ta.rsi(df['close'], length=14)
    
    return df

def get_signal(row, position):
    ema12 = row['EMA_12']
    ema26 = row['EMA_26']
    ema200 = row['EMA_200']
    rsi = row['RSI_14']
    close_price = row['close']
    
    # Pastikan data indikator sudah terbentuk (mencegah error NaN di awal data)
    if str(ema200) == 'nan' or str(rsi) == 'nan':
        return "HOLD"
    
    # Logic LONG (BUY)
    if not position or position['type'] == 'SHORT':
        # Syarat: 
        # 1. Tren mayor sedang naik (Harga di atas EMA 200)
        # 2. Tren minor mulai naik (EMA 12 cross EMA 26)
        # 3. Momentum jelas (RSI di atas 55, bukan 50 agar tidak terjebak sideways)
        if (close_price > ema200) and (ema12 > ema26) and (rsi > 55):
            return "BUY"
            
    # Logic SHORT (SELL)
    if not position or position['type'] == 'LONG':
        # Syarat: 
        # 1. Tren mayor sedang turun (Harga di bawah EMA 200)
        # 2. Tren minor mulai turun (EMA 12 di bawah EMA 26)
        # 3. Momentum jelas (RSI di bawah 45)
        if (close_price < ema200) and (ema12 < ema26) and (rsi < 45):
            return "SELL"
            
    return "HOLD"