"""
Market Data Routes untuk Trading Command Center
API endpoints untuk market data dan real-time updates
"""

from fastapi import APIRouter, Depends, HTTPException, Query
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
async def get_supported_symbols():
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
async def get_realtime_data(symbol: str):
    """Get real-time market data untuk symbol"""
    try:
        # Get dari market data manager
        from main import market_data_manager
        
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
async def get_all_realtime_data():
    """Get semua real-time market data"""
    try:
        from main import market_data_manager
        
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
    symbol: str,
    days: int = Query(default=30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session)
):
    """Get historical market data untuk symbol"""
    try:
        from main import market_data_manager
        
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
    market_type: str = Query(default="all", regex="^(all|indonesia|us|crypto)$")
):
    """Get market heatmap data"""
    try:
        from main import market_data_manager
        
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
                'color': await self._get_heatmap_color(change_percent)
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
    limit: int = Query(default=10, ge=1, le=50),
    market_type: str = Query(default="all", regex="^(all|indonesia|us|crypto)$")
):
    """Get top gainers dan losers"""
    try:
        from main import market_data_manager
        
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


async def _get_heatmap_color(self, change_percent: float) -> str:
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


@router.get("/economic-calendar")
async def get_economic_calendar():
    """Get economic calendar events"""
    try:
        # Mock economic calendar data (dalam production, integrate dengan API)
        today = datetime.now().date()
        events = [
            {
                "date": today.isoformat(),
                "time": "08:30",
                "currency": "USD",
                "event": "Non-Farm Payrolls",
                "impact": "High",
                "actual": "",
                "forecast": "180K",
                "previous": "150K"
            },
            {
                "date": today.isoformat(),
                "time": "10:00",
                "currency": "USD",
                "event": "ISM Manufacturing PMI",
                "impact": "High",
                "actual": "",
                "forecast": "48.5",
                "previous": "47.6"
            },
            {
                "date": today.isoformat(),
                "time": "14:00",
                "currency": "USD",
                "event": "Fed Chair Powell Speech",
                "impact": "High",
                "actual": "",
                "forecast": "",
                "previous": ""
            }
        ]
        
        return {
            "status": "success",
            "data": events,
            "total_events": len(events),
            "date": today.isoformat()
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting economic calendar: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/fear-greed-index")
async def get_fear_greed_index():
    """Get Fear & Greed Index"""
    try:
        # Mock Fear & Greed Index (dalam production, hit actual API)
        current_value = 65  # Neutral ke Fearful
        
        # Determine sentiment
        if current_value >= 75:
            sentiment = "Extreme Greed"
            color = "#ff4444"
        elif current_value >= 55:
            sentiment = "Greed"
            color = "#ff8844"
        elif current_value >= 45:
            sentiment = "Neutral"
            color = "#ffff44"
        elif current_value >= 25:
            sentiment = "Fear"
            color = "#44ff44"
        else:
            sentiment = "Extreme Fear"
            color = "#44ffff"
            
        return {
            "status": "success",
            "data": {
                "value": current_value,
                "sentiment": sentiment,
                "color": color,
                "timestamp": datetime.now().isoformat(),
                "components": {
                    "stock_price_strength": 70,
                    "stock_price_momentum": 60,
                    "market_volatility": 55,
                    "put_call_ratio": 65,
                    "junk_bond_demand": 75,
                    "safe_haven_demand": 45
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting Fear & Greed Index: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")