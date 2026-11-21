# Trading Command Center (TCC)

Dashboard trading untuk saham IDX, saham AS, dan kripto dengan data pasar nyata, 12 strategi sinyal,
model ML yang benar-benar dilatih, **AI Brain** yang menyesuaikan strategi dari hasilnya sendiri, paper trading,
notifikasi, dan update realtime lewat WebSocket.

> Paper trading saja. Bukan nasihat investasi.

## 100% gratis, tanpa API key, tanpa langganan

| Data | Sumber utama | Cadangan bila gagal |
|---|---|---|
| Harga & candle saham IDX/AS | Yahoo Finance | cache terakhir tetap dipakai (Stooq sudah memasang verifikasi anti-bot) |
| Harga kripto | Yahoo Finance (`BTC-USD`) | CoinGecko (`/simple/price`) |
| Kalender ekonomi | Forex Factory (`ff_calendar_thisweek.json`, cache 1 jam) | daftar kosong + pesan |
| Berita IDX & IHSG | Google News RSS (bahasa Indonesia) | cache berita terakhir |
| Berita global & kripto | Yahoo Finance search | cache berita terakhir |
| Database | SQLite | – |
| Notifikasi | Telegram Bot / Discord webhook / browser | – |

Cek keterjangkauan semua sumber: `GET /api/health/market-data`. Binance (ccxt) tidak dipakai karena memblokir
sebagian wilayah (HTTP 451), sedangkan Alpha Vantage, Finnhub, dan NewsAPI tidak dipakai karena butuh pendaftaran key.

## Yang dikerjakan sistem

| Bagian | Cara kerja |
|---|---|
| **Data pasar** | Satu unduhan batch Yahoo Finance tiap ≥60 detik untuk ~125 simbol (IDX, AS, kripto via `BTC-USD`). Candle harian 1 tahun disimpan di memori untuk strategi; fundamental (PER, PBV, market cap) diambil terpisah tiap 6 jam. Kurs USD/IDR ikut diunduh. |
| **Sinyal** | 10 strategi teknikal (EMA, SuperTrend+RSI, Bollinger+MACD, VWAP 20 hari, breakout, mean reversion, liquidity sweep, golden cross, Heikin-Ashi), fundamental, sentimen berita, dan ML. Semua sinyal divalidasi: BUY wajib SL < entry < TP, SELL wajib TP < entry < SL. |
| **ML Ensemble** | RandomForest + XGBoost + LogisticRegression, target "naik dalam 5 hari", dilatih ulang harian pada semua simbol. Diuji out-of-sample pada 20% periode terakhir (dengan jeda anti-bocor). Sinyal hanya keluar bila akurasi uji ≥ 52% dan probabilitas ≥ 60%. Akurasi saat ditulis ±54–55%: sedikit di atas tebakan, dan sistem melaporkannya apa adanya. |
| **AI Brain** | Sinyal ditutup saat kena SL/TP atau kedaluwarsa (P&L dari arah sinyal). Tiap 5 menit, strategi dengan ≥20 sinyal tertutup dinilai: expectancy negatif → ambang confidence +2; win rate < 35% dari ≥40 sinyal → strategi dimatikan; untung dan win rate ≥ 55% → ambang −1. Disimpan di DB, tampil di halaman **AI Brain**. |
| **Paper trading** | Modal awal `INITIAL_CAPITAL` IDR, fee beli/jual, lot IDX 100 lembar, maksimum posisi, auto-exit SL/TP, kurva ekuitas harian, statistik (win rate, profit factor, drawdown, Sharpe). Sinyal BUY bisa dieksekusi langsung dari halaman Signals. |
| **Berita & sentimen** | Saham IDX & IHSG dari Google News RSS, global & kripto dari Yahoo Finance; skor sentimen leksikon (Inggris & Indonesia). Bila tak ada berita untuk sebuah simbol, sentimen kosong, tidak dikarang. |
| **Screener** | Gainers, losers, volume explosion, breakout N hari, oversold (RSI 14), custom; dihitung dari data pasar terbaru. |
| **Fear & Greed** | Indeks internal 0–100 dari semesta simbol: breadth, % di atas MA50, kedekatan ke high/low 52 minggu, volatilitas 20 hari vs 1 tahun. |
| **Notifikasi** | Telegram, Discord, browser (WebSocket). Price alert (di atas/di bawah/perubahan %). Pengaturan & riwayat tersimpan di `data/notifications.json`. |

| **Kalender ekonomi** | Event minggu ini dari Forex Factory yang berdampak Medium/High (plus semua event IDR), waktu dalam WIB. |

## Generate: kerangka berpikir dengan dua gerbang kualitas

Halaman **Generate** menyusun kerangka 7 tahap (masalah → fakta → pengalaman → hipotesis → 7 alternatif dari
7 pola pikir → keputusan + pre-mortem → rencana belajar) untuk kasus *peluang aset*, *masalah strategi*,
*risiko portofolio*, atau *teks bebas*. Setiap keputusan melewati:

| Gerbang | Kapan | Yang diperiksa | Bila gagal |
|---|---|---|---|
| **1 · Preflight** | sebelum generate (`POST /api/insight/preflight`, tombol *Cek dulu*) | kesegaran data, harga valid, ≥ 60/200 candle, anomali (lonjakan > 25%, high < low), analog ≥ 30 kejadian, berita, pengalaman sinyal, akurasi model ML | generate **diblokir** (HTTP 422) dengan daftar perbaikan |
| **2 · Quality control** | sebelum menjawab | konsistensi arah vs bukti, SL < harga < TP, margin keputusan, jumlah & kesepakatan bukti, **uji ketahanan (ablation)**: rekomendasi dibangun ulang tanpa tiap bukti, rekam jejak pola pikir, grounding narasi, **ukuran posisi maksimum** dari `RISK_PER_TRADE` | rekomendasi **diturunkan** ke TUNDA/RISET (yang asli tetap terlihat) |

Hasilnya: skor **keyakinan 0–100** (peringatan kedua gerbang mengurangi skor; dikali stabilitas ablation),
**advokat setan** (argumen terkuat melawan keputusan), dan keputusan akhir. Semua tersimpan di riwayat; hasil
keputusan (otomatis setelah 7 hari untuk kasus peluang) menjadi pengalaman berikutnya.

## Menjalankan

### Docker (disarankan)

```bash
cp .env.example .env          # isi TELEGRAM_* / DISCORD_* bila perlu
docker compose up -d --build
```

Buka `http://localhost` (nginx). Backend langsung: `http://localhost:8000/docs`.
Data SQLite & log tersimpan di `backend/data` dan `backend/logs`.

### Manual

```bash
# backend (Python 3.12+)
pip install -r requirements.txt
cd backend && uvicorn main:app --port 8000

# frontend (Node 20+), dari root proyek
npm install
npm run dev                   # http://localhost:3000, proxy /api /ws /health ke :8000
```

Data pertama muncul ±10–20 detik setelah backend start; model ML dilatih ±1 menit setelahnya.

## Konfigurasi penting (`.env`)

| Variabel | Default | Arti |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/trading.db` | Folder dibuat otomatis |
| `UPDATE_INTERVAL` | `60` | Detik; minimal efektif 60 (unduhan batch) |
| `MIN_CONFIDENCE_SCORE` | `70` | Ambang awal sinyal; AI Brain menyesuaikan per strategi |
| `DEBUG` | `false` | `true` menampilkan detail error ke klien |
| `INITIAL_CAPITAL` | `100000000` | Modal paper trading (IDR) |
| `BUY_FEE` / `SELL_FEE` | `0.0015` / `0.0025` | Fee per sisi |
| `MAX_POSITIONS` | `10` | Posisi terbuka maksimum |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | – | Notifikasi Telegram |
| `DISCORD_WEBHOOK_URL` | – | Notifikasi Discord |

Daftar simbol ada di `backend/config.py`.

## Tes

```bash
cd backend && python -m pytest -q     # unit + integrasi AI Brain (SQLite sungguhan)
npm run typecheck                      # dari root proyek
```

## Batasan yang perlu diketahui

- **Tanpa autentikasi.** API (termasuk order paper trading dan pengaturan) terbuka untuk siapa pun yang bisa
  mengakses server. Jalankan hanya di jaringan pribadi atau di balik proxy yang memakai login.
- Data Yahoo Finance tidak resmi dan bisa terlambat atau dibatasi rate; candle harian, bukan intraday.
- Akurasi ML yang sedikit di atas 50% bukan jaminan keuntungan.
