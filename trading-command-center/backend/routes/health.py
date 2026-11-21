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


@router.get("/market-data")
async def market_data_health():
    """Market data services health check"""
    try:
        # Test market data providers
        services = {}
        
        # Test yfinance
        try:
            import yfinance as yf
            ticker = yf.Ticker("AAPL")
            info = ticker.info
            services["yfinance"] = {
                "status": "healthy",
                "data_available": "currentPrice" in info
            }
        except Exception as e:
            services["yfinance"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            
        # Test Finnhub (if API key available)
        if settings.finnhub_api_key:
            try:
                import finnhub
                fh = finnhub.Client(api_key=settings.finnhub_api_key)
                quote = fh.quote("AAPL")
                services["finnhub"] = {
                    "status": "healthy",
                    "data_available": "c" in quote
                }
            except Exception as e:
                services["finnhub"] = {
                    "status": "unhealthy",
                    "error": str(e)
                }
        else:
            services["finnhub"] = {
                "status": "disabled",
                "reason": "No API key configured"
            }
            
        return {
            "status": "healthy",
            "services": services
        }
        
    except Exception as e:
        logger.error(f"❌ Market data health check error: {e}")
        raise HTTPException(status_code=500, detail="Market data health check failed")


@router.get("/websocket")
async def websocket_health():
    """WebSocket health check"""
    try:
        # Get WebSocket statistics
        from main import websocket_manager
        
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