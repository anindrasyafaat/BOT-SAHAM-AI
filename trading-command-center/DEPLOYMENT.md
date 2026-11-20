# Trading Command Center - Deployment Guide

## 🚀 Quick Start (One-Click Deploy)

### Prerequisites
- Docker & Docker Compose
- Git
- API Keys (Alpha Vantage, Finnhub, News API)

### 1. Clone Repository
```bash
git clone https://github.com/yourusername/trading-command-center.git
cd trading-command-center
```

### 2. Configure Environment
```bash
# Copy environment file
cp .env.example .env

# Edit .env dengan API keys Anda
nano .env
```

### 3. One-Click Deploy
```bash
# Make script executable
chmod +x deploy.sh

# Deploy Trading Command Center
./deploy.sh
```

### 4. Access Dashboard
- **Frontend**: http://localhost:3000
- **API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 📋 Manual Deployment

### Docker Compose Method (Recommended)

```bash
# Build and start services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Installation

#### Backend Setup
```bash
cd backend

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build
```

## 🔧 Configuration

### Environment Variables (.env)

#### Required API Keys
```bash
# Market Data APIs
ALPHA_VANTAGE_API_KEY=your_key_here
FINNHUB_API_KEY=your_key_here
NEWS_API_KEY=your_key_here

# Notifications (Optional)
TELEGRAM_BOT_TOKEN=your_bot_token
DISCORD_WEBHOOK_URL=your_webhook_url
```

#### Trading Parameters
```bash
# Risk Management
MAX_POSITIONS=10
RISK_PER_TRADE=0.02
MIN_CONFIDENCE_SCORE=70

# Update Intervals
UPDATE_INTERVAL=10
```

### Get Free API Keys

1. **Alpha Vantage** (US Stock Data)
   - Website: https://www.alphavantage.co/support/#api-key
   - Free: 5 API calls per minute, 500 calls per day

2. **Finnhub** (Real-time Stock Data)
   - Website: https://finnhub.io/
   - Free: 60 calls per minute

3. **News API** (Market News)
   - Website: https://newsapi.org/
   - Free: 100 requests per day

## 🐳 Docker Commands

### Basic Operations
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Restart services
docker-compose restart

# View logs
docker-compose logs -f
docker-compose logs backend
docker-compose logs frontend

# Update services
docker-compose pull
docker-compose up -d
```

### Advanced Operations
```bash
# Rebuild specific service
docker-compose build backend
docker-compose up -d backend

# Execute commands in container
docker-compose exec backend python -c "print('Hello from container!')"
docker-compose exec frontend npm run build

# Access container shell
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 🏗️ Architecture Overview

### Services
- **Backend (FastAPI)**: Port 8000
- **Frontend (React)**: Port 3000
- **Redis**: Port 6379
- **Nginx**: Port 80 (Reverse Proxy)

### Data Flow
```
User → Nginx → Frontend (React)
           ↓
       Backend (FastAPI) → Market Data APIs
           ↓
       Redis (Caching) → Database (SQLite)
```

## 📊 Features Overview

### 1. Market Dashboard
- Real-time market data
- Heatmap visualization
- Top movers tracking
- Market sentiment analysis

### 2. AI Signal Generator
- 12 trading strategies
- Machine learning ensemble
- Risk management
- Performance tracking

### 3. Portfolio Management
- Paper trading
- Position tracking
- P&L analysis
- Risk metrics

### 4. Market Screening
- Custom filters
- Technical analysis
- Volume analysis
- Breakout detection

## 🔍 Troubleshooting

### Common Issues

#### 1. Services Not Starting
```bash
# Check Docker status
docker system info

# Check container logs
docker-compose logs

# Restart services
docker-compose restart
```

#### 2. API Connection Issues
```bash
# Test API endpoint
curl http://localhost:8000/health

# Check network connectivity
docker network ls
docker network inspect trading-command-center_default
```

#### 3. Database Issues
```bash
# Check database file
ls -la backend/data/

# Reset database (backup first!)
rm backend/data/trading.db
docker-compose restart backend
```

#### 4. Frontend Build Issues
```bash
# Clear node modules
rm -rf frontend/node_modules
rm frontend/package-lock.json

# Reinstall dependencies
cd frontend && npm install
```

## 📈 Performance Optimization

### 1. Resource Allocation
```bash
# Increase memory limits in docker-compose.yml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 2G
```

### 2. Caching Configuration
```bash
# Redis optimization
REDIS_MAXMEMORY=512mb
REDIS_POLICY=allkeys-lru
```

### 3. Database Optimization
```bash
# SQLite optimization
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;
PRAGMA cache_size=10000;
```

## 🔒 Security Considerations

### 1. API Key Security
- Never commit API keys to repository
- Use environment variables
- Rotate keys regularly

### 2. Network Security
```bash
# Configure firewall
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 8000/tcp  # Restrict to specific IPs
ufw enable
```

### 3. SSL/TLS Setup
```bash
# For production deployment with SSL
docker-compose -f docker-compose.yml -f docker-compose.ssl.yml up -d
```

## 📊 Monitoring

### Health Checks
```bash
# System health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/database

# Redis health
curl http://localhost:8000/health/redis
```

### Metrics
```bash
# System resources
curl http://localhost:8000/health/resources

# WebSocket stats
curl http://localhost:8000/health/websocket
```

## 🚀 Production Deployment

### 1. VPS Setup
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Install Docker Compose
sudo apt install docker-compose-plugin
```

### 2. Domain & SSL
```bash
# Setup domain
sudo apt install nginx certbot python3-certbot-nginx

# Configure SSL
sudo certbot --nginx -d yourdomain.com
```

### 3. Deploy
```bash
# Clone repository
git clone https://github.com/yourusername/trading-command-center.git
cd trading-command-center

# Configure environment
cp .env.example .env
nano .env  # Edit with your configurations

# Deploy
./deploy.sh
```

## 📞 Support

### Getting Help
1. Check logs: `docker-compose logs`
2. API Documentation: http://localhost:8000/docs
3. Health Check: http://localhost:8000/health
4. GitHub Issues: Report bugs and feature requests

### Community
- Discord: [Join our community](https://discord.gg/tradingcc)
- Documentation: [Full documentation](https://docs.tradingcommandcenter.com)
- Email: support@tradingcommandcenter.com

## 🔄 Updates

### Update to Latest Version
```bash
# Pull latest changes
git pull origin main

# Update containers
./deploy.sh update
```

### Backup Before Updates
```bash
# Backup database
cp backend/data/trading.db backend/data/trading.db.backup

# Backup environment
cp .env .env.backup
```

## 🎯 Next Steps

After successful deployment:

1. **Configure API Keys** in `.env` file
2. **Setup Notifications** (Telegram/Discord)
3. **Customize Trading Parameters**
4. **Add Symbols to Watchlist**
5. **Monitor Performance**

---

**Happy Trading!** 🚀

For more information, visit our [documentation](https://docs.tradingcommandcenter.com)