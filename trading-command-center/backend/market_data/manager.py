"""
Market Data Manager untuk Trading Command Center
Mengelola pengambilan dan distribusi real-time market data
"""

import asyncio
from typing import Dict, List, Optional
from datetime import datetime
import math
import pandas as pd
import yfinance as yf
from database.connection import AsyncSessionLocal
from models.market_data import MarketData, MarketSummary, SectorPerformance
from config import settings, get_supported_symbols
from utils.logger import setup_logging

logger = setup_logging()

HISTORY_PERIOD = "1y"          # cukup untuk EMA/MACD/BB/SMA200 harian
FUNDAMENTAL_REFRESH = 6 * 3600
FX_SYMBOL = "USDIDR=X"  # ticker.info lambat & dibatasi rate, cukup beberapa kali sehari


def yahoo_symbol(symbol: str) -> str:
    """BTCUSDT -> BTC-USD (Yahoo); saham tetap."""
    return symbol[:-4] + "-USD" if symbol.endswith("USDT") else symbol


def _num(v):
    try:
        f = float(v)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


class MarketDataManager:
    """Manager market data: satu unduhan batch Yahoo per siklus untuk saham IDX, AS, dan kripto."""

    def __init__(self, websocket_manager):
        self.websocket_manager = websocket_manager
        self.running = False
        # Unduhan batch ~150 simbol butuh puluhan detik; jangan lebih sering dari 60 detik.
        self.update_interval = max(settings.update_interval, 60)
        self.symbols = {k: list(dict.fromkeys(v)) for k, v in get_supported_symbols().items()}
        self.market_type_of = {s: k for k, v in self.symbols.items() for s in v}

        self.market_data_cache: Dict[str, Dict] = {}
        self.history: Dict[str, pd.DataFrame] = {}
        self.fundamentals: Dict[str, Dict] = {}
        self.usd_idr: Optional[float] = None
        self.last_refresh: Optional[datetime] = None
        self.last_error: Optional[str] = None
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        logger.info("🚀 Starting Market Data Manager...")
        self.running = True
        self._tasks = [
            asyncio.create_task(self._update_loop()),
            asyncio.create_task(self._fundamental_loop()),
            asyncio.create_task(self._market_summary_loop()),
        ]
        logger.info("✅ Market Data Manager started")

    async def stop(self):
        logger.info("🛑 Stopping Market Data Manager...")
        self.running = False
        for t in self._tasks:
            t.cancel()
        logger.info("✅ Market Data Manager stopped")

    async def _update_loop(self):
        while self.running:
            try:
                await self.refresh()
            except Exception as e:
                self.last_error = str(e)
                logger.error(f"❌ Error in update loop: {e}")
            await asyncio.sleep(self.update_interval)

    def _download(self) -> Dict[str, pd.DataFrame]:
        symbols = list(self.market_type_of)
        raw = yf.download(
            [yahoo_symbol(s) for s in symbols] + [FX_SYMBOL], period=HISTORY_PERIOD, interval="1d",
            group_by="ticker", auto_adjust=False, threads=True, progress=False,
        )
        frames = {}
        for s in symbols:
            try:
                df = raw[yahoo_symbol(s)].dropna(subset=["Close"])
            except KeyError:
                continue
            if len(df) >= 2:
                frames[s] = df
        try:
            self.usd_idr = float(raw[FX_SYMBOL]["Close"].dropna().iloc[-1])
        except (KeyError, IndexError):
            logger.warning("⚠️ Kurs USD/IDR tidak tersedia; nilai aset USD belum dikonversi")
        return frames

    async def refresh(self):
        """Ambil candle terbaru semua simbol lalu perbarui cache, DB, dan WebSocket."""
        frames = await asyncio.to_thread(self._download)
        if not frames:
            raise RuntimeError("Yahoo Finance tidak mengembalikan data (cek koneksi/ rate limit)")
        rows = []
        for symbol, df in frames.items():
            self.history[symbol] = df
            data = self._quote(symbol, df)
            self.market_data_cache[symbol] = data
            rows.append(data)
            await self.websocket_manager.broadcast(
                {"type": "market_update", "symbol": symbol, "data": data}, channel="market_data"
            )
        await self._save_market_data_batch(rows)
        from notifications.manager import NotificationManager
        await NotificationManager().check_price_alerts(self.market_data_cache)
        from paper.broker import check_exits
        await check_exits(self)
        self.last_refresh, self.last_error = datetime.now(), None
        logger.info(f"📈 Market data refreshed: {len(frames)}/{len(self.market_type_of)} symbols")

    def _quote(self, symbol: str, df: pd.DataFrame) -> dict:
        last, prev = df.iloc[-1], df.iloc[-2]
        price, prev_close = float(last["Close"]), float(prev["Close"])
        info = self.fundamentals.get(symbol, {})
        crypto = self.market_type_of.get(symbol) == "crypto"
        year = df.tail(252)
        change = price - prev_close
        return {
            "symbol": symbol,
            "name": info.get("name") or symbol,
            "current_price": price,
            "open_price": float(last["Open"]),
            "high_price": float(last["High"]),
            "low_price": float(last["Low"]),
            "close_price": prev_close,
            "volume": _num(last["Volume"]) or 0.0,
            "volume_avg": _num(df["Volume"].tail(20).mean()),
            "market_cap": info.get("market_cap"),
            "pe_ratio": info.get("pe_ratio"),
            "pb_ratio": info.get("pb_ratio"),
            "dividend_yield": info.get("dividend_yield"),
            "change_amount": change,
            "change_percent": change / prev_close * 100 if prev_close else 0.0,
            "market_type": "crypto" if crypto else "stock",
            "exchange": info.get("exchange") or ("CRYPTO" if crypto else ("IDX" if symbol.endswith(".JK") else "US")),
            "currency": info.get("currency") or ("USD" if crypto or not symbol.endswith(".JK") else "IDR"),
            "day_high": float(last["High"]),
            "day_low": float(last["Low"]),
            "fifty_two_week_high": float(year["High"].max()),
            "fifty_two_week_low": float(year["Low"].min()),
            "timestamp": datetime.now(),
        }

    def _fetch_fundamental(self, symbol: str) -> dict:
        info = yf.Ticker(yahoo_symbol(symbol)).info or {}
        return {
            "name": info.get("longName") or info.get("shortName"),
            "market_cap": _num(info.get("marketCap")),
            "pe_ratio": _num(info.get("trailingPE")),
            "pb_ratio": _num(info.get("priceToBook")),
            "dividend_yield": _num(info.get("dividendYield")),
            "exchange": info.get("exchange"),
            "currency": info.get("currency"),
            "sector": info.get("sector"),
        }

    async def _fundamental_loop(self):
        await asyncio.sleep(5)  # beri jalan unduhan harga lebih dulu
        while self.running:
            for symbol in list(self.market_type_of):
                if not self.running:
                    return
                try:
                    self.fundamentals[symbol] = await asyncio.to_thread(self._fetch_fundamental, symbol)
                    if symbol in self.market_data_cache:
                        self.market_data_cache[symbol].update(
                            {k: v for k, v in self.fundamentals[symbol].items() if v is not None and k != "sector"}
                        )
                except Exception as e:
                    logger.warning(f"⚠️ Fundamental {symbol}: {e}")
                await asyncio.sleep(1)  # sopan terhadap rate limit Yahoo
            await asyncio.sleep(FUNDAMENTAL_REFRESH)

    async def _save_market_data_batch(self, rows: List[dict]):
        try:
            async with AsyncSessionLocal() as session:
                session.add_all(MarketData(**r) for r in rows)
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
            
    def to_idr(self, symbol: str) -> Optional[float]:
        """Faktor konversi harga simbol ke IDR (None bila kurs belum ada)."""
        return 1.0 if symbol.endswith(".JK") else self.usd_idr

    def get_market_data(self, symbol: str) -> Optional[dict]:
        """Get market data dari cache"""
        return self.market_data_cache.get(symbol)
        
    def get_all_market_data(self) -> dict:
        """Get semua market data"""
        return self.market_data_cache.copy()
        
    async def get_historical_data(self, symbol: str, days: int = 30) -> List[dict]:
        """Candle harian (OHLCV) terakhir `days` hari dari unduhan Yahoo."""
        df = self.history.get(symbol)
        if df is None:
            return []
        return [
            {
                "timestamp": ts.isoformat(),
                "open_price": float(r["Open"]), "high_price": float(r["High"]),
                "low_price": float(r["Low"]), "close_price": float(r["Close"]),
                "volume": _num(r["Volume"]) or 0.0,
            }
            for ts, r in df.tail(days).iterrows()
        ]
