"""
Market Data Routes untuk Trading Command Center
API endpoints untuk market data dan real-time updates
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from collections import defaultdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db_session
from models.market_data import MarketData, MarketSummary, SectorPerformance
from market_data.manager import MarketDataManager
from config import get_supported_symbols
from utils.logger import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/symbols")
async def list_supported_symbols():
    """Get semua symbols yang didukung"""
    try:
        symbols = get_supported_symbols()
        return {
            "status": "success",
            "data": symbols,
            "total_indonesia": len(symbols["indonesia"]),
            "total_us": len(symbols["us"]),
            "total_crypto": len(symbols["crypto"])
        }
    except Exception as e:
        logger.error(f"❌ Error getting supported symbols: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/realtime/{symbol}")
async def get_realtime_data(symbol: str, request: Request):
    """Get real-time market data untuk symbol"""
    try:
        # Get dari market data manager
        market_data_manager = getattr(request.app.state, "market_data_manager", None)
        
        if not market_data_manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
            
        data = market_data_manager.get_market_data(symbol)
        
        if not data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
            
        return {
            "status": "success",
            "symbol": symbol,
            "data": data,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting real-time data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/realtime")
async def get_all_realtime_data(request: Request):
    """Get semua real-time market data"""
    try:
        market_data_manager = getattr(request.app.state, "market_data_manager", None)
        
        if not market_data_manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
            
        all_data = market_data_manager.get_all_market_data()
        
        return {
            "status": "success",
            "data": all_data,
            "total_symbols": len(all_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting all real-time data: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/historical/{symbol}")
async def get_historical_data(
    request: Request,
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session)
):
    """Get historical market data untuk symbol"""
    try:
        market_data_manager = getattr(request.app.state, "market_data_manager", None)
        
        if not market_data_manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
            
        historical_data = await market_data_manager.get_historical_data(symbol, days)
        
        if not historical_data:
            raise HTTPException(status_code=404, detail=f"No historical data found for {symbol}")
            
        return {
            "status": "success",
            "symbol": symbol,
            "data": historical_data,
            "total_records": len(historical_data),
            "period_days": days,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting historical data for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/market-summary")
async def get_market_summary():
    """Get market summary untuk semua market types"""
    try:
        from sqlalchemy import select, desc
        from database.connection import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get latest market summary untuk setiap market type
            market_types = ["indonesia", "us", "crypto"]
            summaries = {}
            
            for market_type in market_types:
                stmt = (
                    select(MarketSummary)
                    .where(MarketSummary.market_type == market_type)
                    .order_by(desc(MarketSummary.timestamp))
                    .limit(1)
                )
                
                result = await session.execute(stmt)
                summary = result.scalar_one_or_none()
                
                if summary:
                    summaries[market_type] = summary.to_dict()
                    
            return {
                "status": "success",
                "data": summaries,
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting market summary: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sectors")
async def get_sector_performance():
    """Get sector performance data"""
    try:
        from sqlalchemy import select, desc
        from database.connection import AsyncSessionLocal
        
        async with AsyncSessionLocal() as session:
            # Get latest sector performance
            stmt = (
                select(SectorPerformance)
                .order_by(desc(SectorPerformance.timestamp))
                .limit(50)  # 50 latest records
            )
            
            result = await session.execute(stmt)
            sectors = result.scalars().all()
            
            # Group by market type
            sector_data = defaultdict(list)
            for sector in sectors:
                sector_data[sector.market_type].append(sector.to_dict())
                
            return {
                "status": "success",
                "data": dict(sector_data),
                "total_records": len(sectors),
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        logger.error(f"❌ Error getting sector performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/heatmap")
async def get_market_heatmap(
    request: Request,
    market_type: str = Query(default="all", pattern="^(all|indonesia|us|crypto)$")
):
    """Get market heatmap data"""
    try:
        market_data_manager = getattr(request.app.state, "market_data_manager", None)
        
        if not market_data_manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
            
        all_data = market_data_manager.get_all_market_data()
        
        # Filter berdasarkan market type
        if market_type != "all":
            symbols = get_supported_symbols()[market_type]
            filtered_data = {k: v for k, v in all_data.items() if k in symbols}
        else:
            filtered_data = all_data
            
        # Prepare heatmap data
        heatmap_data = []
        for symbol, data in filtered_data.items():
            change_percent = data.get('change_percent', 0)
            heatmap_data.append({
                'symbol': symbol,
                'name': data.get('name', symbol),
                'price': data.get('current_price', 0),
                'change': data.get('change_amount', 0),
                'change_percent': change_percent,
                'volume': data.get('volume', 0),
                'market_cap': data.get('market_cap', 0),
                'color': _get_heatmap_color(change_percent)
            })
            
        # Sort by change percent
        heatmap_data.sort(key=lambda x: x['change_percent'], reverse=True)
        
        return {
            "status": "success",
            "data": heatmap_data,
            "market_type": market_type,
            "total_symbols": len(heatmap_data),
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting market heatmap: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/top-movers")
async def get_top_movers(
    request: Request,
    limit: int = Query(default=10, ge=1, le=50),
    market_type: str = Query(default="all", pattern="^(all|indonesia|us|crypto)$")
):
    """Get top gainers dan losers"""
    try:
        market_data_manager = getattr(request.app.state, "market_data_manager", None)
        
        if not market_data_manager:
            raise HTTPException(status_code=503, detail="Market data manager not available")
            
        all_data = market_data_manager.get_all_market_data()
        
        # Filter berdasarkan market type
        if market_type != "all":
            symbols = get_supported_symbols()[market_type]
            filtered_data = {k: v for k, v in all_data.items() if k in symbols}
        else:
            filtered_data = all_data
            
        # Sort by change percent
        sorted_data = sorted(
            filtered_data.items(),
            key=lambda x: x[1].get('change_percent', 0),
            reverse=True
        )
        
        # Top gainers
        top_gainers = [
            {
                'symbol': symbol,
                'name': data.get('name', symbol),
                'price': data.get('current_price', 0),
                'change': data.get('change_amount', 0),
                'change_percent': data.get('change_percent', 0),
                'volume': data.get('volume', 0)
            }
            for symbol, data in sorted_data[:limit]
        ]
        
        # Top losers
        top_losers = [
            {
                'symbol': symbol,
                'name': data.get('name', symbol),
                'price': data.get('current_price', 0),
                'change': data.get('change_amount', 0),
                'change_percent': data.get('change_percent', 0),
                'volume': data.get('volume', 0)
            }
            for symbol, data in sorted_data[-limit:]
        ]
        
        # Most active by volume
        most_active = sorted(
            filtered_data.items(),
            key=lambda x: x[1].get('volume', 0),
            reverse=True
        )[:limit]
        
        most_active_data = [
            {
                'symbol': symbol,
                'name': data.get('name', symbol),
                'price': data.get('current_price', 0),
                'volume': data.get('volume', 0),
                'volume_avg': data.get('volume_avg', 0),
                'change_percent': data.get('change_percent', 0)
            }
            for symbol, data in most_active
        ]
        
        return {
            "status": "success",
            "data": {
                "top_gainers": top_gainers,
                "top_losers": top_losers,
                "most_active": most_active_data
            },
            "market_type": market_type,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error getting top movers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


def _get_heatmap_color(change_percent: float) -> str:
    """Get heatmap color berdasarkan change percent"""
    try:
        if change_percent >= 5:
            return "#00ff00"  # Bright green
        elif change_percent >= 3:
            return "#40ff40"  # Green
        elif change_percent >= 1:
            return "#80ff80"  # Light green
        elif change_percent >= 0:
            return "#c0ffc0"  # Very light green
        elif change_percent >= -1:
            return "#ffc0c0"  # Very light red
        elif change_percent >= -3:
            return "#ff8080"  # Light red
        elif change_percent >= -5:
            return "#ff4040"  # Red
        else:
            return "#ff0000"  # Bright red
            
    except Exception as e:
        logger.error(f"❌ Error getting heatmap color: {e}")
        return "#808080"  # Gray for error


def fear_greed(quotes: dict, history: dict) -> Optional[dict]:
    """Indeks Fear & Greed internal (0-100) dari semesta simbol yang dipantau."""
    if not quotes:
        return None
    clamp = lambda v: int(max(0, min(100, round(v))))
    breadth = 100 * sum(q["change_percent"] > 0 for q in quotes.values()) / len(quotes)
    above_ma50 = highs = lows = n_hist = 0
    vol_ratios = []
    for sym, df in history.items():
        c = df["Close"]
        if len(c) < 60:
            continue
        n_hist += 1
        above_ma50 += c.iloc[-1] > c.tail(50).mean()
        hi, lo = df["High"].tail(252).max(), df["Low"].tail(252).min()
        highs += c.iloc[-1] >= hi * 0.95
        lows += c.iloc[-1] <= lo * 1.05
        r = c.pct_change()
        long_vol = r.tail(252).std()
        if long_vol and long_vol == long_vol:
            vol_ratios.append(r.tail(20).std() / long_vol)
    if not n_hist:
        return None
    components = {
        "market_breadth": clamp(breadth),
        "price_momentum": clamp(100 * above_ma50 / n_hist),
        "price_strength": clamp(50 + 50 * (highs - lows) / n_hist),
        "market_volatility": clamp(50 - 100 * (sum(vol_ratios) / len(vol_ratios) - 1)) if vol_ratios else 50,
    }
    value = clamp(sum(components.values()) / len(components))
    sentiment = ("Extreme Greed" if value >= 75 else "Greed" if value >= 55 else "Neutral" if value >= 45
                 else "Fear" if value >= 25 else "Extreme Fear")
    return {"value": value, "sentiment": sentiment, "components": components,
            "symbols": n_hist, "timestamp": datetime.now().isoformat()}


CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"  # Forex Factory: gratis, tanpa API key
_calendar_cache: dict = {"at": None, "events": []}


def calendar_events(raw: list, now: datetime, past: bool = False) -> list:
    """Event berdampak Medium/High (plus semua event IDR), waktu WIB. past=True: event yang sudah lewat."""
    from zoneinfo import ZoneInfo
    wib = ZoneInfo("Asia/Jakarta")
    out = []
    for e in raw:
        try:
            when = datetime.fromisoformat(e["date"]).astimezone(wib)
        except (KeyError, ValueError):
            continue
        if (when < now.astimezone(wib)) != past or (e.get("impact") not in ("High", "Medium") and e.get("country") != "IDR"):
            continue
        out.append({
            "date": when.date().isoformat(), "time": when.strftime("%d %b %H:%M WIB") + (" (lewat)" if past else ""),
            "currency": e.get("country", ""), "event": e.get("title", ""), "impact": e.get("impact", "Low"),
            "actual": "", "forecast": e.get("forecast", ""), "previous": e.get("previous", ""),
        })
    return sorted(out, key=lambda x: (x["date"], x["time"]), reverse=past)


@router.get("/economic-calendar")
async def get_economic_calendar(limit: int = Query(15, ge=1, le=100)):
    """Kalender ekonomi minggu ini dari Forex Factory (di-cache 1 jam agar sopan terhadap sumber)."""
    import httpx
    now = datetime.now().astimezone()
    if _calendar_cache["at"] is None or (now - _calendar_cache["at"]).total_seconds() > 3600:
        try:
            async with httpx.AsyncClient(timeout=15, headers={"User-Agent": "TradingCommandCenter/1.0"}) as c:
                r = await c.get(CALENDAR_URL)
                r.raise_for_status()
                _calendar_cache.update(at=now, events=r.json())
        except Exception as e:
            logger.warning(f"⚠️ Kalender ekonomi tidak bisa diambil: {e}")
            if not _calendar_cache["events"]:
                return {"status": "success", "data": [], "source": None, "message": "Sumber kalender sedang tidak bisa diakses"}
    data = calendar_events(_calendar_cache["events"], now)[:limit]
    if data:
        return {"status": "success", "data": data, "source": "Forex Factory", "total_events": len(data)}
    # akhir pekan: jadwal minggu depan baru terbit; tampilkan event penting minggu ini yang sudah lewat
    data = calendar_events(_calendar_cache["events"], now, past=True)[:limit]
    return {"status": "success", "data": data, "source": "Forex Factory", "total_events": len(data),
            "message": "Belum ada jadwal mendatang; menampilkan event minggu ini yang sudah lewat"}


@router.get("/fear-greed-index")
async def get_fear_greed_index(request: Request):
    mdm = getattr(request.app.state, "market_data_manager", None)
    data = fear_greed(mdm.get_all_market_data(), mdm.history) if mdm else None
    if data is None:
        raise HTTPException(status_code=503, detail="Data pasar belum siap")
    return {"status": "success", "data": data}
