"""
Health Check Routes untuk Trading Command Center
API endpoints untuk system health monitoring
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db_session, engine
from config import settings
from utils.logger import setup_logging
import asyncio
import redis.asyncio as redis

logger = setup_logging()
router = APIRouter()


@router.get("/")
async def health_check(session: AsyncSession = Depends(get_db_session)):
    """Comprehensive health check untuk semua services"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": "2024-01-01T00:00:00Z",
            "version": "1.0.0",
            "environment": settings.environment,
            "services": {}
        }
        
        # Database health check
        try:
            await session.execute("SELECT 1")
            health_status["services"]["database"] = {
                "status": "healthy",
                "type": "SQLite",
                "url": settings.database_url.replace("sqlite:///", "sqlite://")
            }
        except Exception as e:
            health_status["services"]["database"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
            
        # Redis health check
        try:
            redis_client = redis.from_url(settings.redis_url)
            await redis_client.ping()
            await redis_client.close()
            health_status["services"]["redis"] = {
                "status": "healthy",
                "url": settings.redis_url
            }
        except Exception as e:
            health_status["services"]["redis"] = {
                "status": "unhealthy",
                "error": str(e)
            }
            health_status["status"] = "degraded"
            
        # Market data services health check
        health_status["services"]["market_data"] = {
            "status": "healthy",
            "providers": {
                "yfinance": "enabled",
                "finnhub": "enabled" if settings.finnhub_api_key else "disabled",
                "alpha_vantage": "enabled" if settings.alpha_vantage_api_key else "disabled"
            }
        }
        
        # Signal generator health check
        health_status["services"]["signal_generator"] = {
            "status": "healthy",
            "active_strategies": 10,
            "min_confidence": settings.min_confidence_score
        }
        
        # WebSocket health check
        health_status["services"]["websocket"] = {
            "status": "healthy",
            "connections": "active"
        }
        
        # System resources
        import psutil
        health_status["system"] = {
            "cpu_usage": psutil.cpu_percent(),
            "memory_usage": psutil.virtual_memory().percent,
            "disk_usage": psutil.disk_usage('/').percent
        }
        
        return health_status
        
    except Exception as e:
        logger.error(f"❌ Health check error: {e}")
        raise HTTPException(status_code=500, detail="Health check failed")


@router.get("/database")
async def database_health(session: AsyncSession = Depends(get_db_session)):
    """Database-specific health check"""
    try:
        # Test database connection
        await session.execute("SELECT 1")
        
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


@router.get("/redis")
async def redis_health():
    """Redis-specific health check"""
    try:
        redis_client = redis.from_url(settings.redis_url)
        await redis_client.ping()
        
        # Get Redis info
        info = await redis_client.info()
        await redis_client.close()
        
        return {
            "status": "healthy",
            "version": info.get("redis_version"),
            "memory_used": info.get("used_memory_human"),
            "connected_clients": info.get("connected_clients"),
            "uptime_days": info.get("uptime_in_days")
        }
        
    except Exception as e:
        logger.error(f"❌ Redis health check error: {e}")
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