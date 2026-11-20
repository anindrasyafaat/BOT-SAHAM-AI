# Trading Command Center (TCC)

🚀 **Professional AI Trading Agent dengan Real-Time Market Data & Signal Generation**

TCC adalah platform trading command center profesional yang menyediakan real-time market data, AI-generated trading signals, dan dashboard interaktif untuk trading saham Indonesia, US stocks, dan cryptocurrency.

## ✨ Fitur Utama

### 📊 Market Overview Dashboard Real-Time
- **Heatmap** 100+ saham IHSG, 50+ US stocks, 50+ cryptocurrency
- **Top Gainers/Losers/Most Active** dengan update tiap 10 detik
- **Market Breadth**: Advancers vs Decliners, New High vs New Low
- **Sector Performance** 11 sektor BEI + US sectors
- **Fear & Greed Index**, VIX, CNN Fear & Greed, Crypto Fear & Greed
- **Economic Calendar** dengan highlight high impact events
- **Live News Feed** dengan sentiment score
- **Currency Strength Meter** dan **Bond Yield Monitor**

### 🤖 AI Signal Generator
**12 Strategi Built-in:**
1. **EMA Crossover** (8/21) + Volume Profile
2. **SuperTrend ATR** + RSI Divergence  
3. **Bollinger Bands Squeeze** + MACD
4. **VWAP** + Order Block (ICT Concept)
5. **Breakout 52-week high** + Volume Surge
6. **Mean Reversion** + Z-score
7. **Liquidity Sweep Detector**
8. **Golden Cross / Death Cross**
9. **Heikin-Ashi Trend Following**
10. **Machine Learning Ensemble** (XGBoost + LSTM)

### 🎯 Signal Quality
- **Confidence Score** 0-100%
- **Entry Price, TP1, TP2, SL** yang jelas
- **Risk/Reward Ratio** dan expected duration
- **Technical + Fundamental + Sentiment Analysis**

### 📈 Dashboard Fitur
- **Dark Mode** profesional seperti TradingView
- **Live Candlestick Charts** dengan TradingView Lightweight Charts
- **Watchlist Customizable** (drag & drop)
- **Signal History Table** dengan filter win rate
- **Performance Metrics**: Win Rate, Profit Factor, Max DD, Sharpe Ratio
- **News Sentiment Timeline**
- **Screener Otomatis**: Gap Up, Volume Explosion, RSI Oversold
- **Alert Sound** + Browser Notification

## 🛠️ Technology Stack

### Backend (Python 3.12)
- **FastAPI** - Web framework modern dan cepat
- **WebSocket & SSE** - Real-time data streaming
- **SQLAlchemy** - ORM untuk database
- **Redis** - Caching dan session management
- **yfinance, investpy, ccxt pro** - Market data providers
- **pandas-ta, ta-lib, vectorbt** - Technical analysis
- **XGBoost, TensorFlow, PyTorch** - Machine learning
- **APScheduler, Celery** - Background tasks

### Frontend (React 19 + TypeScript)
- **React 19** dengan Concurrent Features
- **TypeScript** untuk type safety
- **Tailwind CSS** + **Shadcn/ui** untuk UI components
- **Recharts** untuk data visualization
- **TradingView Lightweight Charts** untuk candlestick charts
- **Socket.io-client** untuk WebSocket communication
- **React Query** untuk data fetching dan caching

### Infrastructure
- **Docker & Docker Compose** untuk containerization
- **Nginx** sebagai reverse proxy
- **Redis** untuk caching real-time
- **SQLite** untuk data persistence

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.12+
- Node.js 20+
- Git

### Installation

1. **Clone Repository**
```bash
git clone https://github.com/yourusername/trading-command-center.git
cd trading-command-center
```

2. **Setup Environment Variables**
```bash
cp .env.example .env
# Edit .env dengan API keys Anda
```

3. **One-Click Deploy dengan Docker**
```bash
docker-compose up -d
```

4. **Akses Dashboard**
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Documentation: http://localhost:8000/docs

### Manual Installation

#### Backend Setup
```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

#### Frontend Setup
```bash
cd frontend
npm install
npm run dev
```

## 📁 Project Structure

```
trading-command-center/
├── backend/                    # FastAPI Backend
│   ├── main.py                # Entry point
│   ├── config.py              # Configuration
│   ├── database/              # Database models & connection
│   ├── models/                # SQLAlchemy models
│   ├── routes/                # API endpoints
│   ├── market_data/           # Market data management
│   ├── signals/               # Signal generation
│   ├── strategies/            # Trading strategies
│   ├── websocket/             # WebSocket handling
│   ├── utils/                 # Utility functions
│   └── requirements.txt       # Python dependencies
│
├── frontend/                  # React Frontend
│   ├── src/
│   │   ├── components/        # React components
│   │   ├── pages/             # Page components
│   │   ├── hooks/             # Custom React hooks
│   │   ├── lib/               # Utility functions
│   │   └── App.tsx            # Main App component
│   ├── package.json           # Node.js dependencies
│   └── vite.config.ts         # Vite configuration
│
├── docker-compose.yml         # Docker orchestration
├── Dockerfile.backend         # Backend Docker image
├── Dockerfile.frontend        # Frontend Docker image
└── README.md                  # Documentation
```

## 🔧 Configuration

### Environment Variables (.env)
```env
# API Keys
ALPHA_VANTAGE_API_KEY=your_alpha_vantage_key
FINNHUB_API_KEY=your_finnhub_key
NEWS_API_KEY=your_news_api_key
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
DISCORD_WEBHOOK_URL=your_discord_webhook

# Database
DATABASE_URL=sqlite:///data/trading.db
REDIS_URL=redis://localhost:6379

# Trading Parameters
MAX_POSITIONS=10
RISK_PER_TRADE=0.02
MIN_CONFIDENCE_SCORE=70
```

### Trading Parameters
- **Risk Per Trade**: Default 2% dari portfolio
- **Max Positions**: Maximum 10 posisi simultan
- **Confidence Threshold**: Minimum 70% untuk signal generation
- **Signal Expiry**: 24 jam untuk signal validity

## 📊 API Endpoints

### Market Data
- `GET /api/market/symbols` - Get supported symbols
- `GET /api/market/realtime/{symbol}` - Real-time market data
- `GET /api/market/historical/{symbol}` - Historical data
- `GET /api/market/heatmap` - Market heatmap
- `GET /api/market/top-movers` - Top gainers/losers

### Signals
- `GET /api/signals` - Get active signals
- `GET /api/signals/history` - Signal history
- `GET /api/signals/performance` - Strategy performance

### WebSocket
- `ws://localhost:8000/ws` - Real-time data streaming
- Channels: `market_data`, `signals`, `news`

## 🎯 Trading Signals Format

```json
{
  "symbol": "BBCA.JK",
  "signal_type": "BUY",
  "strategy_name": "EMA_Crossover",
  "confidence_score": 85,
  "entry_price": 9750,
  "target_price_1": 10250,
  "target_price_2": 10800,
  "stop_loss": 9400,
  "risk_reward_ratio": 2.1,
  "technical_analysis": "EMA bullish crossover with volume confirmation",
  "generated_at": "2024-01-01T10:00:00Z"
}
```

## 🔔 Notifications

### Channels yang Didukung
- **Telegram Bot** - Pesan dengan emoji dan formatting
- **Discord Webhook** - Rich embed messages
- **Browser Push** - Native browser notifications
- **Sound Alerts** - Audio notifications

### Format Notifikasi
```
🚀 SIGNAL BARU - BBCA.JK
Signal: STRONG BUY
Entry: Rp 9.750 - Rp 9.850
TP1: Rp 10.250 (+4.8%)
TP2: Rp 10.800 (+10%)
SL: Rp 9.400 (-3.8%)
Confidence: 92%
Strategy: EMA Crossover + Volume
Timeframe: Daily
```

## 📈 Performance Metrics

### Strategy Performance
- **Win Rate**: Persentase signal yang profitable
- **Profit Factor**: Ratio gross profit / gross loss
- **Max Drawdown**: Maximum peak-to-trough decline
- **Sharpe Ratio**: Risk-adjusted return
- **Average R:R**: Average risk/reward ratio

### Real-time Monitoring
- **Connection Status**: WebSocket health check
- **Data Latency**: Real-time data delay
- **Signal Accuracy**: Backtesting results
- **System Performance**: Response time dan uptime

## 🛡️ Security & Best Practices

### Security Features
- **API Key Management**: Secure storage dan rotation
- **Rate Limiting**: Prevent API abuse
- **Input Validation**: SQL injection dan XSS protection
- **CORS Configuration**: Controlled cross-origin access
- **HTTPS Enforcement**: Secure communication

### Risk Management
- **Position Sizing**: Otomatis berdasarkan risk tolerance
- **Stop Loss**: Otomatis untuk setiap signal
- **Max Drawdown**: Daily loss limits
- **Correlation Check**: Avoid overexposure

## 🧪 Testing

### Unit Tests
```bash
cd backend
pytest tests/
```

### Integration Tests
```bash
docker-compose -f docker-compose.test.yml up
```

### Load Testing
```bash
# WebSocket load test
npm run test:websocket

# API load test
npm run test:api
```

## 🚀 Deployment

### Production Deployment
1. **Setup VPS/Cloud Server**
2. **Configure Domain & SSL**
3. **Setup Monitoring (Prometheus/Grafana)**
4. **Configure Backup Strategy**
5. **Deploy dengan Docker Compose**

### Monitoring
- **Health Checks**: API dan database status
- **Performance Metrics**: Response time, throughput
- **Error Tracking**: Sentry integration
- **Uptime Monitoring**: External service checks

## 🤝 Contributing

1. Fork repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push ke branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **TradingView** untuk Lightweight Charts
- **Yahoo Finance** untuk market data
- **Alpha Vantage** untuk fundamental data
- **Finnhub** untuk real-time data
- **Shadcn/ui** untuk UI components

## 📞 Support

- **Documentation**: [https://docs.tradingcommandcenter.com](https://docs.tradingcommandcenter.com)
- **Discord Community**: [https://discord.gg/tradingcc](https://discord.gg/tradingcc)
- **Email Support**: support@tradingcommandcenter.com
- **GitHub Issues**: [Report Bug/Feature Request](https://github.com/yourusername/trading-command-center/issues)

---

**⚠️ Disclaimer**: Trading Command Center adalah untuk educational dan research purposes. Semua trading signals adalah rekomendasi dan tidak menjamin profit. Selalu lakukan risk management yang tepat dan jangan investasi lebih dari yang Anda mampu untuk kehilangan.

**🚀 Happy Trading!**
## 🧠 AI Brain (strategi yang belajar sendiri)

Setiap 5 menit `SignalGenerator` menilai tiap strategi dari sinyal yang sudah ditutup (`backend/signals/learning.py`):

| Kondisi (≥20 sinyal tertutup) | Tindakan |
|---|---|
| Expectancy negatif | Ambang confidence naik +2 (maks 95), lebih selektif |
| Expectancy negatif, win rate < 35%, ≥40 sinyal | Strategi dimatikan (aktifkan lagi manual) |
| Expectancy positif, win rate ≥ 55% | Ambang turun −1 (min 60), lebih banyak peluang |

Ambang hasil belajar disimpan di `strategy_configs`, jadi tetap berlaku setelah restart, dan dipakai saat validasi sinyal.
Pantau di halaman **AI Brain** (`/brain`) atau `GET /api/signals/brain`.

Tes: `cd backend && python3 -m signals.test_learning`
