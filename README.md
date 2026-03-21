# [✔] 411 BOT AI | NATIVE SYNC CORE v8.0

> **AUTHOR**: VERSAAGONON / VERSAA (411 MASTER)  
> **ENGINE**: NATIVE DATA STREAMING (NO-AI TRADING MODE)  
> **LICENSE**: EXCLUSIVE HACKER ACCESS

---

## 1. PENDAHULUAN: APAKAH INI GIMMICK?
Sistem ini adalah **TECHNICAL ALGORITHMIC TRADING ENGINE**. 
- **BUKAN GIMMICK**: Keputusan BUY/SELL diambil berdasarkan perhitungan matematika murni dari harga historis (Indicators).
- **BUKAN CHEAT**: Bot tidak melihat data masa depan untuk menentukan "Decision". Bot hanya membaca harga saat ini (Candle Close) and menggunakan indikator untuk masuk/keluar.
- **BUKAN PREDIKSI GAIB**: Strategi ini menggunakan "Trend Following" and "Momentum RSI".

**GROUND TRUTH (EXPECTED MOVE)**:  
Kami sengaja menampilkan indikator "Expected Move" di Dashboard sebagai **Tolok Ukur Kejujuran (Ground Truth)**. Indikator ini memang "mengintip" data 5 menit ke depan hanya untuk memberi tahu Tuan apakah keputusan Algoritma Bot (Buy/Sell) sesuai dengan pergerakan pasar yang sebenarnya atau tidak.

---

## 2. METODE PELATIHAN & STRATEGI
Sistem ini menggunakan metode **Backtesting Execution** terhadap dataset `btc_2024_2025.json`.

### A. Algoritma Inti (Fast-Track v8.0)
Bot menggunakan kombinasi 3 indikator utama:
1. **EMA 12 (Exponential Moving Average)**: Garis tren jangka pendek (Cepat).
2. **EMA 26 (Exponential Moving Average)**: Garis tren jangka menengah (Lambat).
3. **RSI 9 (Relative Strength Index)**: Alat pengukur momentum & overbought/oversold.

**LOGIKA EKSEKUSI (BUY)**:
- Terjadi **Golden Cross**: EMA 12 memotong ke atas EMA 26.
- **RSI Momentum**: Nilai RSI di atas 50 (Menandakan tren naik sedang kuat).

**LOGIKA EKSEKUSI (SELL/EXIT)**:
- Terjadi **Death Cross**: EMA 12 memotong ke bawah EMA 26.
- **RSI Overbought**: Nilai RSI menyentuh angka 80 (Sudah jenuh beli).

### B. Money Management (Lot Size)
Bot menggunakan sistem **Fixed Fractional Sizing**:
- **Lot**: Menggunakan **50% dari sisa Saldo (Balance)** untuk setiap posisi.
- **Profit**: Keuntungan langsung ditambahkan ke Balance untuk Compound Interest (Bunga Berbudi).
- **Initial Capital**: $10,000.00.

---

## 3. ALUR KERJA SISTEM (PIPELINE)

1. **DATA INGESTION**: Server Python memuat file `btc_2024_2025.json` (8,800+ data).
2. **INDICATOR CALCULATION**: `pandas_ta` menghitung semua EMA and RSI sebelum simulasi dimulai.
3. **LOOP SIMULATION**: Server memulai perputaran waktu (0.04 detik per data).
4. **DECISION MAKING**: Di setiap detak jantung data, algoritma mengevaluasi kondisi Buy/Sell.
5. **NATIVE STREAMING (SYNC)**:
   - Data Harga, Log, and Ekuitas dikirim dalam satu paket JSON via WebSocket.
   - Browser menerima paket and menggambarnya di **HTML5 Canvas** (Native Rendering).
   - **Zero-Delay**: Log and Grafik tersinkronisasi 1:1.

---

## 4. TRANSPARANSI ENGINE
Bot ini dirancang untuk menunjukkan realitas trading:
- **Win Rate**: Dihitung berdasarkan berapa kali 'Decision' bot cocok dengan 'Ground Truth' (Market Move).
- **Equity Curve**: Menunjukkan pertumbuhan (atau penurunan) modal secara visual.
- **P/L Display**: Menghitung Total Profit/Loss komulatif dari titik awal modal $10,000.

---

## 5. CARA MENJALANKAN (Hacker Way)
1. **Install Dependencies**: `pip install flask flask-socketio pandas pandas_ta`
2. **Run Server**: `python dashboard/server.py`
3. **Access**: Buka `http://127.0.0.1:5000` di Browser.
4. **Action**: Tekan **Ctrl + F5** (Hard Refresh) lalu Klik **START TRADING ENGINE**.

---
*DIBUAT OLEH ASISTEN ANTI-GRAVITY ATAS PERINTAH SANG MULIA VERSAAGONON.*
