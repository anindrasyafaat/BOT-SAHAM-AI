"""
Main FastAPI Application untuk Trading Command Center
Entry point utama untuk backend trading command center
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

import auth
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import internal modules
from config import settings
from database.connection import init_database
from websocket.manager import ConnectionManager
from routes import (
    market_data, signals, portfolio, 
    screener, news, notifications, health, insight
)
from market_data.manager import MarketDataManager
from signals.generator import SignalGenerator
from utils.logger import setup_logging


# Setup logging
logger = setup_logging()

# Global managers
market_data_manager: MarketDataManager = None
signal_generator: SignalGenerator = None
websocket_manager: ConnectionManager = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager untuk startup dan shutdown"""
    auth.check_startup()
    global market_data_manager, signal_generator, websocket_manager
    
    # Startup
    logger.info("🚀 Starting Trading Command Center Backend...")
    
    try:
        # Initialize database
        await init_database()
        logger.info("✅ Database initialized")
        
        # Initialize WebSocket manager
        websocket_manager = ConnectionManager()
        from notifications.manager import NotificationManager
        NotificationManager.websocket_manager = websocket_manager
        logger.info("✅ WebSocket manager initialized")
        
        # Initialize market data manager
        market_data_manager = MarketDataManager(websocket_manager)
        await market_data_manager.start()
        app.state.market_data_manager = market_data_manager
        logger.info("✅ Market data manager started")
        
        # Initialize signal generator
        signal_generator = SignalGenerator(market_data_manager, websocket_manager)
        await signal_generator.start()
        app.state.signal_generator = signal_generator
        logger.info("✅ Signal generator started")
        
        logger.info("🎉 Trading Command Center Backend Ready!")
        
    except Exception as e:
        logger.error(f"❌ Startup error: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Trading Command Center...")
    
    try:
        if market_data_manager:
            await market_data_manager.stop()
            logger.info("✅ Market data manager stopped")
            
        if signal_generator:
            await signal_generator.stop()
            logger.info("✅ Signal generator stopped")
            
        logger.info("👋 Trading Command Center Backend Shutdown Complete")
        
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")


# Create FastAPI app instance
app = FastAPI(
    title="Trading Command Center API",
    description="Professional AI Trading Agent dengan real-time market data dan signal generation",
    version="1.0.0",
    lifespan=lifespan
)

# CORS: hanya origin terdaftar; tanpa cookie (auth memakai header Bearer)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def require_login(request, call_next):
    """Satu titik penegakan auth untuk seluruh /api/* (kecuali login/status)."""
    path = request.url.path
    if (auth.enabled() and path.startswith("/api") and request.method != "OPTIONS"
            and path not in auth.PUBLIC_PATHS and not auth.verify(auth.bearer(request.headers.get("authorization")))):
        return JSONResponse(status_code=401, content={"detail": "Login diperlukan"})
    return await call_next(request)


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


@app.get("/api/auth/status")
async def auth_status(request: Request):
    return {"required": auth.enabled(),
            "authenticated": auth.verify(auth.bearer(request.headers.get("authorization")))}


@app.post("/api/auth/login")
async def auth_login(body: LoginIn):
    if not auth.enabled():
        return {"token": None, "required": False}
    if auth.throttled():
        raise HTTPException(status_code=429, detail="Terlalu banyak percobaan, tunggu 1 menit")
    token = auth.login(body.password)
    if not token:
        raise HTTPException(status_code=401, detail="Password salah")
    return {"token": token, "required": True}



# Root endpoint
@app.get("/")
async def root():
    """Root endpoint untuk health check"""
    return {
        "message": "Trading Command Center API",
        "version": "1.0.0",
        "status": "running",
        "environment": settings.environment
    }


# WebSocket endpoint untuk real-time data
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint untuk real-time market data dan signals"""
    if not auth.verify(websocket.query_params.get("token")):
        await websocket.close(code=1008)  # policy violation: belum login
        return
    await websocket_manager.connect(websocket)
    
    try:
        while True:
            # Terima message dari client
            data = await websocket.receive_json()
            
            # Handle berbagai tipe message
            message_type = data.get("type")
            
            if message_type == "subscribe":
                # Subscribe ke market data atau signals
                symbol = data.get("symbol")
                channel = data.get("channel", "market_data")
                
                await websocket_manager.subscribe(websocket, channel, symbol)
                
            elif message_type == "unsubscribe":
                # Unsubscribe dari channel
                symbol = data.get("symbol")
                channel = data.get("channel", "market_data")
                
                await websocket_manager.unsubscribe(websocket, channel, symbol)
                
            elif message_type == "get_signals":
                # Request signals untuk symbol
                symbol = data.get("symbol")
                signals = await signal_generator.get_signals(symbol)
                
                await websocket_manager.send_personal_message(websocket, {
                    "type": "signals",
                    "symbol": symbol,
                    "data": signals
                })
                
    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.close()


# Include routers
app.include_router(market_data.router, prefix="/api/market", tags=["Market Data"])
app.include_router(signals.router, prefix="/api/signals", tags=["Signals"])
app.include_router(portfolio.router, prefix="/api/portfolio", tags=["Portfolio"])
app.include_router(screener.router, prefix="/api/screener", tags=["Screener"])
app.include_router(news.router, prefix="/api/news", tags=["News"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(health.router, prefix="/api/health", tags=["Health"])
app.include_router(insight.router, prefix="/api/insight", tags=["Generate"])


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler untuk semua error"""
    logger.error(f"Global error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": str(exc) if settings.debug else "Terjadi kesalahan di server",
            "path": str(request.url)
        }
    )


# Health check endpoint (status nyata layanan internal)
@app.get("/health")
async def health_check():
    from datetime import datetime
    mdm = market_data_manager
    ready = bool(mdm and mdm.market_data_cache)
    return {
        "status": "healthy" if ready else "starting",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "market_data": {
                "symbols": len(mdm.market_data_cache) if mdm else 0,
                "last_refresh": mdm.last_refresh.isoformat() if mdm and mdm.last_refresh else None,
                "last_error": mdm.last_error if mdm else None,
            },
            "signals": "running" if signal_generator and signal_generator.running else "stopped",
            "websocket": websocket_manager.get_connection_stats() if websocket_manager else None,
        },
    }


if __name__ == "__main__":
    # Jalankan server untuk development
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )