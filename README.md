# 411 QUANT TERMINAL AI 
### PRESET v19.0 | PERFORMANCE AUDIT ENGINE

---

## ╔══════════════════════════════════════════╗
## ║          PANDUAN OPERASIONAL             ║
## ╚══════════════════════════════════════════╝

Selamat datang di arsitektur trading tercanggih, Master Versaa. Sistem ini dirancang untuk simulasi and eksekusi trading aset kripto (BTC/USDT) menggunakan berbagai model kecerdasan buatan.

### 1. MODEL ARSITEKTUR (STRATEGY)
Sistem ini dilengkapi dengan 4 otak trading yang dapat dipilih secara dinamis:
- **GEMINI-3-PRO**: Algoritma Scalping Agresif. Berfokus pada pergerakan harga kecil dengan frekuensi tinggi.
- **GEMINI-3-FLASH**: Versi yang lebih cepat dari Pro, dioptimalkan untuk responsivitas maksimal pada volatilitas tinggi.
- **CLAUDE-SONNET-4.6**: Model "Multi-Confirmation Trend Confluence". Paling akurat and hati-hati (EMA + RSI + MACD + ATR + Bollinger Filter).
- **CHATGPT**: Algoritma berbasis kombinasi indikator klasik yang stabil untuk tren jangka menengah.

---

### 2. GLOSARIUM TERMINOLOGI (TRADING 101)
Agar Master dapat memahami setiap log operasional, berikut adalah penjelasannya:

| Istilah | Penjelasan Teknis |
| :--- | :--- |
| **LONG (BUY)** | Membuka posisi beli. Bot memprediksi harga akan naik. Keuntungan didapat jika harga jual lebih tinggi dari harga beli. |
| **SHORT (SELL)** | Membuka posisi jual (meminjam asset). Bot memprediksi harga akan turun. Keuntungan didapat jika harga turun (Tuan untung saat harga hancur). |
| **COVER SHORT** | Menutup posisi SHORT. Bot membeli kembali asset untuk dikembalikan, and mengunci keuntungan dari penurunan harga. |
| **CLOSE LONG** | Menjual asset yang dimiliki pada posisi LONG untuk mengamankan profit atau membatasi kerugian. |
| **EQUITY** | Nilai total saldo Tuan saat ini (Modal + Profit/Loss yang sedang berjalan). |
| **PNL (Profit/Loss)** | Selisih keuntungan atau kerugian yang dihasilkan dari seluruh trade. |
| **ATR (Volatility)** | Pengukur gejolak pasar. Jika ATR tinggi, pasar sangat liar. Jika rendah, pasar tenang/sideways. |

---

### 3. FITUR UNGGULAN
- **DASHBOARD REAL-TIME**: Visualisasi pergerakan dana and sinyal trading secara live.
- **HYPER SPEED**: Simulasi data 1 tahun hanya dalam hitungan menit (Normal, Fast, Super Speed).
- **AUTOMATED PDF AUDIT**: Menghasilkan laporan formal yang mencakup ROI, Rata-rata Profit Harian, Bulanan, and Tahunan.
- **CONTINUOUS SESSION**: Fitur Restart otomatis tanpa harus mematikan program utama.

---

### 4. CARA MENJALANKAN
1. Pastikan seluruh dependensi Python (Flask, Pandas, FPDF) terinstal.
2. Jalankan server: `python dashboard/server.py`.
3. Akses via Browser: `http://localhost:5000`.
4. Pilih Modal, Strategi, and Kecepatan, lalu klik **START TRADING ENGINE**.

### 5. PANDUAN TRADING & PERSIAPAN PRODUCTION

**🔥 REKOMENDASI TIMEFRAME (TF) & GAYA TRADING:**
Sistem and algoritma (khususnya Claude-Sonnet v2.0 and ChatGPT) yang dilatih pada engine ini dirancang kokoh untuk membaca tren *Medium-to-Long* secara simetris (Bilateral).
- **Timeframe Terbaik**: `1H` (1 Jam) hingga `4H` (4 Jam). Data BTC yang kita gunakan juga sangat cocok di rentang ini.
- **Gaya Trading**: **Swing Trading / Trend Following** (Main Hold). 
- **Peringatan Keras**: Algoritma ini **TIDAK COCOK** untuk metode transaksi cepat atau *Scalping* (TF 1m / 5m). Mesin ini dibangun dengan filosofi *Anti-Overtrade*. Ia memiliki filter ADX, Minimum Hold Period, and Cooldown timer. Artinya, mesin lebih suka menahan posisi ('*Hold*') selama berjam-jam untuk memakan gelombang tren besar daripada keluar-masuk market setiap menit yang berujung pada kerugian akibat *Trading Fee* and *Slippage*.

**⚙️ SYARAT DEPLOYMENT (PRODUCTION READINESS):**
Setelah pengujian simulasi memuaskan, jika Master Versaa ingin menginkarnasikan otak AI ini ke bursa sungguhan (Real Market seperti Binance/Bybit), berikut 5 fondasi yang wajib dibangun:
1. **Market Data Stream (WebSockets)**: Ganti asupan data dari file `.json` lokal menjadi koneksi WebSockets (`wss://stream.binance.com`) agar AI menerima data *Real-Time Tick-by-Tick*.
2. **Order Execution Interface (API)**: Di dalam `server.py`, ketika AI melempar konfirmasi `signal == "BUY"`, gantilah simulasi balance awal dengan perintah tembak asli ke exchange API (misal menggunakan library `ccxt.create_market_order()`).
3. **Slippage & Exchange Fee Impact**: Kondisi real mengandung biaya *Maker/Taker* (0.02% - 0.05%) and *Slippage* (selip harga pasar). Parameter filter kemenangan harus dinaikkan untuk menutupi biaya ini agar tidak "Winner in Simulation, Loser in Production."
4. **Hard Stop-Loss Server-side**: Jangan hanya mengandalkan kode script untuk keluar posisi. Jika internet terputus, bot rusak. Segera ikatkan OCO Order (Hard SL & TP) langsung di server Exchange saat order pertama dikirim.
5. **Bot Resiliency (Auto-Reconnect)**: Tambahkan proteksi agar bot tidak mati jika API Exchange merespon "Error 500" atau "Rate Limit Exceeded". Bot harus kebal and bisa me-restart koneksinya sendiri.

---

### PREPARED BY: 411 ENGINE ADAPTIVE AI
*Didedikasikan sepenuhnya untuk: VERSAA MASTER X 411*
