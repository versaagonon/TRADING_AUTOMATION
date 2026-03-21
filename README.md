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

---

### PREPARED BY: 411 ENGINE ADAPTIVE AI
*Didedikasikan sepenuhnya untuk: VERSAA MASTER 411*
