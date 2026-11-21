"""
Health Check Routes untuk Trading Command Center
API endpoints untuk system health monitoring
"""

from fastapi import Request, APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db_session, engine
from config import settings
from utils.logger import setup_logging
import asyncio

logger = setup_logging()
router = APIRouter()


@router.get("/")
async def health_check(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Health check nyata: database, data pasar, signal generator, websocket, resource sistem."""
    import psutil
    from datetime import datetime
    from sqlalchemy import text

    status = {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "1.0.0",
              "environment": settings.environment, "services": {}}
    try:
        await session.execute(text("SELECT 1"))
        status["services"]["database"] = {"status": "healthy", "type": settings.database_url.split(":")[0]}
    except Exception as e:
        status["services"]["database"] = {"status": "unhealthy", "error": str(e)}
        status["status"] = "degraded"

    mdm = getattr(request.app.state, "market_data_manager", None)
    md_ok = bool(mdm and mdm.market_data_cache)
    status["services"]["market_data"] = {
        "status": "healthy" if md_ok else "starting", "provider": "yfinance",
        "symbols": len(mdm.market_data_cache) if mdm else 0,
        "last_refresh": mdm.last_refresh.isoformat() if mdm and mdm.last_refresh else None,
        "last_error": mdm.last_error if mdm else None,
    }
    gen = getattr(request.app.state, "signal_generator", None)
    status["services"]["signal_generator"] = {
        "status": "healthy" if gen and gen.running else "stopped",
        "strategies": len(gen.strategy_configs) if gen else 0,
        "enabled": sum(c["enabled"] for c in gen.strategy_configs.values()) if gen else 0,
        "ml_test_accuracy": gen.ml_strategy.test_accuracy if gen else None,
    }
    if not md_ok or not (gen and gen.running):
        status["status"] = "degraded"
    status["system"] = {"cpu_usage": psutil.cpu_percent(), "memory_usage": psutil.virtual_memory().percent,
                        "disk_usage": psutil.disk_usage("/").percent}
    return status


@router.get("/database")
async def database_health(session: AsyncSession = Depends(get_db_session)):
    """Database-specific health check"""
    try:
        # Test database connection
        await session.execute(text("SELECT 1"))
        
        # Get database stats
        from models.market_data import MarketData
        from models.signals import TradingSignal
        
        market_data_count = await session.query(MarketData).count()
        signals_count = await session.query(TradingSignal).count()
        
        return {
            "status": "healthy",
            "database": "SQLite",
            "tables": {
                "market_data": market_data_count,
                "signals": signals_count
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Database health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


FREE_SOURCES = {  # semua gratis tanpa API key
    "yahoo_finance": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=1d&interval=1d",
    "coingecko": "https://api.coingecko.com/api/v3/ping",
    "forex_factory_calendar": "https://nfs.faireconomy.media/ff_calendar_thisweek.json",
    "google_news_rss": "https://news.google.com/rss/search?q=IHSG&hl=id&gl=ID&ceid=ID:id",
}


@router.get("/market-data")
async def market_data_health():
    """Cek keterjangkauan setiap sumber data gratis yang dipakai sistem."""
    import httpx

    async def probe(client, url):
        try:
            r = await client.get(url)
            if r.status_code == 429:  # hidup, tetapi sedang membatasi rate (tier gratis)
                return {"status": "rate_limited", "http": 429}
            return {"status": "healthy" if r.status_code < 400 else "unhealthy", "http": r.status_code}
        except Exception as e:
            return {"status": "unreachable", "error": str(e)}

    async with httpx.AsyncClient(timeout=10, headers={"User-Agent": "Mozilla/5.0 TradingCommandCenter"}) as c:
        results = await asyncio.gather(*(probe(c, u) for u in FREE_SOURCES.values()))
    services = dict(zip(FREE_SOURCES, results))
    ok = all(v["status"] in ("healthy", "rate_limited") for v in services.values())
    return {"status": "healthy" if ok else "degraded", "services": services}


@router.get("/websocket")
async def websocket_health(request: Request):
    """WebSocket health check"""
    try:
        gen = getattr(request.app.state, "signal_generator", None)
        websocket_manager = gen.websocket_manager if gen else None
        
        if websocket_manager:
            stats = websocket_manager.get_connection_stats()
            return {
                "status": "healthy",
                "connections": stats.get("total_connections", 0),
                "channels": stats.get("channels", {})
            }
        else:
            return {
                "status": "unhealthy",
                "error": "WebSocket manager not initialized"
            }
            
    except Exception as e:
        logger.error(f"❌ WebSocket health check error: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }


@router.get("/resources")
async def system_resources():
    """System resource usage"""
    try:
        import psutil
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        
        # Disk usage
        disk = psutil.disk_usage('/')
        
        # Network I/O
        net_io = psutil.net_io_counters()
        
        return {
            "status": "healthy",
            "cpu": {
                "usage_percent": cpu_percent,
                "count": psutil.cpu_count()
            },
            "memory": {
                "total": memory.total,
                "available": memory.available,
                "used": memory.used,
                "percent": memory.percent
            },
            "disk": {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "percent": disk.percent
            },
            "network": {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv
            }
        }
        
    except Exception as e:
        logger.error(f"❌ System resources check error: {e}")
        raise HTTPException(status_code=500, detail="System resources check failed")