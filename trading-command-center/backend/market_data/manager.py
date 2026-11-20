"""
Market Data Manager untuk Trading Command Center
Mengelola pengambilan dan distribusi real-time market data
"""

import asyncio
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import yfinance as yf
import ccxt.pro as ccxt
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import AsyncSessionLocal
from models.market_data import MarketData, MarketSummary, SectorPerformance
from config import settings, get_supported_symbols
from utils.logger import setup_logging

logger = setup_logging()


class MarketDataManager:
    """Manager untuk market data real-time"""
    
    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.running = False
        self.update_interval = settings.update_interval
        self.symbols = get_supported_symbols()
        
        # Data storage
        self.market_data_cache: Dict[str, Dict] = {}
        self.crypto_exchange = None
        
        # Rate limiting
        self.last_update: Dict[str, datetime] = {}
        self.min_update_interval = 5  # seconds
        
    async def start(self):
        """Start market data manager"""
        logger.info("🚀 Starting Market Data Manager...")
        
        self.running = True
        
        # Initialize crypto exchange
        try:
            self.crypto_exchange = ccxt.binance({
                'apiKey': '',
                'secret': '',
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'spot',
                },
            })
            logger.info("✅ Crypto exchange initialized")
        except Exception as e:
            logger.error(f"❌ Failed to initialize crypto exchange: {e}")
        
        # Start background tasks
        asyncio.create_task(self._update_loop())
        asyncio.create_task(self._market_summary_loop())
        
        logger.info("✅ Market Data Manager started")
        
    async def stop(self):
        """Stop market data manager"""
        logger.info("🛑 Stopping Market Data Manager...")
        
        self.running = False
        
        if self.crypto_exchange:
            await self.crypto_exchange.close()
            
        logger.info("✅ Market Data Manager stopped")
        
    async def _update_loop(self):
        """Main update loop untuk market data"""
        while self.running:
            try:
                # Update stock data
                await self._update_stock_data()
                
                # Update crypto data
                await self._update_crypto_data()
                
                # Wait for next update
                await asyncio.sleep(self.update_interval)
                
            except Exception as e:
                logger.error(f"❌ Error in update loop: {e}")
                await asyncio.sleep(10)  # Wait before retrying
                
    async def _update_stock_data(self):
        """Update stock market data"""
        try:
            # Update Indonesia stocks
            for symbol in self.symbols["indonesia"]:
                await self._update_yahoo_stock(symbol)
                
            # Update US stocks
            for symbol in self.symbols["us"]:
                await self._update_yahoo_stock(symbol)
                
        except Exception as e:
            logger.error(f"❌ Error updating stock data: {e}")
            
    async def _update_crypto_data(self):
        """Update crypto market data"""
        try:
            if not self.crypto_exchange:
                return
                
            for symbol in self.symbols["crypto"]:
                await self._update_crypto_price(symbol)
                
        except Exception as e:
            logger.error(f"❌ Error updating crypto data: {e}")
            
    async def _update_yahoo_stock(self, symbol: str):
        """Update stock data dari Yahoo Finance"""
        try:
            # Check rate limiting
            now = datetime.now()
            if symbol in self.last_update:
                if (now - self.last_update[symbol]).total_seconds() < self.min_update_interval:
                    return
                    
            # Get stock data
            ticker = yf.Ticker(symbol)
            info = ticker.info
            
            if not info or 'currentPrice' not in info:
                return
                
            # Extract data
            current_price = info.get('currentPrice', 0)
            open_price = info.get('open', current_price)
            high_price = info.get('dayHigh', current_price)
            low_price = info.get('dayLow', current_price)
            close_price = info.get('previousClose', current_price)
            volume = info.get('volume', 0)
            volume_avg = info.get('averageVolume', 0)
            
            # Calculate changes
            change_amount = current_price - close_price
            change_percent = (change_amount / close_price * 100) if close_price > 0 else 0
            
            # Market data object
            market_data = {
                'symbol': symbol,
                'name': info.get('longName', symbol),
                'current_price': current_price,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': close_price,
                'volume': volume,
                'volume_avg': volume_avg,
                'market_cap': info.get('marketCap'),
                'pe_ratio': info.get('trailingPE'),
                'pb_ratio': info.get('priceToBook'),
                'dividend_yield': info.get('dividendYield'),
                'change_amount': change_amount,
                'change_percent': change_percent,
                'market_type': 'stock',
                'exchange': info.get('exchange', 'Unknown'),
                'currency': info.get('currency', 'USD'),
                'day_high': info.get('dayHigh'),
                'day_low': info.get('dayLow'),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'timestamp': datetime.now(),
            }
            
            # Update cache
            self.market_data_cache[symbol] = market_data
            
            # Save to database
            await self._save_market_data(market_data)
            
            # Update last update time
            self.last_update[symbol] = now
            
            # Broadcast ke WebSocket
            await self.websocket_manager.broadcast({
                'type': 'market_update',
                'symbol': symbol,
                'data': market_data
            }, channel='market_data')
            
        except Exception as e:
            logger.error(f"❌ Error updating stock {symbol}: {e}")
            
    async def _update_crypto_price(self, symbol: str):
        """Update crypto price dari exchange"""
        try:
            # Get ticker data
            ticker = await self.crypto_exchange.fetch_ticker(symbol)
            
            if not ticker or 'last' not in ticker:
                return
                
            current_price = ticker['last']
            open_price = ticker.get('open', current_price)
            high_price = ticker.get('high', current_price)
            low_price = ticker.get('low', current_price)
            volume = ticker.get('baseVolume', 0)
            
            # Calculate changes
            change_amount = current_price - open_price
            change_percent = (change_amount / open_price * 100) if open_price > 0 else 0
            
            # Market data object
            market_data = {
                'symbol': symbol,
                'name': symbol.replace('USDT', '/USD'),
                'current_price': current_price,
                'open_price': open_price,
                'high_price': high_price,
                'low_price': low_price,
                'close_price': open_price,  # Crypto uses open as reference
                'volume': volume,
                'volume_avg': None,
                'market_cap': None,
                'pe_ratio': None,
                'pb_ratio': None,
                'dividend_yield': None,
                'change_amount': change_amount,
                'change_percent': change_percent,
                'market_type': 'crypto',
                'exchange': 'Binance',
                'currency': 'USDT',
                'day_high': high_price,
                'day_low': low_price,
                'fifty_two_week_high': None,
                'fifty_two_week_low': None,
                'timestamp': datetime.now(),
            }
            
            # Update cache
            self.market_data_cache[symbol] = market_data
            
            # Save to database
            await self._save_market_data(market_data)
            
            # Broadcast ke WebSocket
            await self.websocket_manager.broadcast({
                'type': 'market_update',
                'symbol': symbol,
                'data': market_data
            }, channel='market_data')
            
        except Exception as e:
            logger.error(f"❌ Error updating crypto {symbol}: {e}")
            
    async def _save_market_data(self, data: dict):
        """Save market data ke database"""
        try:
            async with AsyncSessionLocal() as session:
                # Create market data record
                market_data = MarketData(**data)
                session.add(market_data)
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Error saving market data: {e}")
            
    async def _market_summary_loop(self):
        """Loop untuk market summary updates"""
        while self.running:
            try:
                await self._update_market_summary()
                await asyncio.sleep(60)  # Update setiap menit
                
            except Exception as e:
                logger.error(f"❌ Error in market summary loop: {e}")
                await asyncio.sleep(10)
                
    async def _update_market_summary(self):
        """Update market summary data"""
        try:
            # Calculate untuk setiap market type
            for market_type in ['indonesia', 'us', 'crypto']:
                await self._calculate_market_summary(market_type)
                
        except Exception as e:
            logger.error(f"❌ Error updating market summary: {e}")
            
    async def _calculate_market_summary(self, market_type: str):
        """Calculate market summary untuk market type"""
        try:
            symbols = self.symbols.get(market_type, [])
            
            total_stocks = len(symbols)
            advancers = 0
            decliners = 0
            unchanged = 0
            
            # Count market breadth
            for symbol in symbols:
                if symbol in self.market_data_cache:
                    data = self.market_data_cache[symbol]
                    change_percent = data.get('change_percent', 0)
                    
                    if change_percent > 0:
                        advancers += 1
                    elif change_percent < 0:
                        decliners += 1
                    else:
                        unchanged += 1
                        
            # Save market summary
            summary = {
                'market_type': market_type,
                'total_stocks': total_stocks,
                'advancers': advancers,
                'decliners': decliners,
                'unchanged': unchanged,
                'timestamp': datetime.now(),
            }
            
            await self._save_market_summary(summary)
            
            # Broadcast update
            await self.websocket_manager.broadcast({
                'type': 'market_summary',
                'market_type': market_type,
                'data': summary
            }, channel='market_data')
            
        except Exception as e:
            logger.error(f"❌ Error calculating market summary for {market_type}: {e}")
            
    async def _save_market_summary(self, summary: dict):
        """Save market summary ke database"""
        try:
            async with AsyncSessionLocal() as session:
                market_summary = MarketSummary(**summary)
                session.add(market_summary)
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Error saving market summary: {e}")
            
    def get_market_data(self, symbol: str) -> Optional[dict]:
        """Get market data dari cache"""
        return self.market_data_cache.get(symbol)
        
    def get_all_market_data(self) -> dict:
        """Get semua market data"""
        return self.market_data_cache.copy()
        
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[dict]:
        """Get historical market data"""
        try:
            async with AsyncSessionLocal() as session:
                # Query historical data
                from sqlalchemy import select, desc
                
                stmt = (
                    select(MarketData)
                    .where(MarketData.symbol == symbol)
                    .order_by(desc(MarketData.timestamp))
                    .limit(days * 24)  # Asumsi hourly data
                )
                
                result = await session.execute(stmt)
                records = result.scalars().all()
                
                return [record.to_dict() for record in records]
                
        except Exception as e:
            logger.error(f"❌ Error getting historical data for {symbol}: {e}")
            return []