"""
Konfigurasi Trading Command Center
File konfigurasi utama untuk semua pengaturan aplikasi
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Kelas konfigurasi utama untuk Trading Command Center"""
    
    # Environment
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    
    # Server Configuration
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # Database
    database_url: str = Field(default="sqlite:///data/trading.db", env="DATABASE_URL")
    
    # Redis Cache
    redis_url: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    redis_ttl: int = Field(default=300, env="REDIS_TTL")  # 5 menit
    
    # API Keys untuk Market Data
    alpha_vantage_api_key: Optional[str] = Field(default=None, env="ALPHA_VANTAGE_API_KEY")
    finnhub_api_key: Optional[str] = Field(default=None, env="FINNHUB_API_KEY")
    news_api_key: Optional[str] = Field(default=None, env="NEWS_API_KEY")
    
    # Notification Channels
    telegram_bot_token: Optional[str] = Field(default=None, env="TELEGRAM_BOT_TOKEN")
    discord_webhook_url: Optional[str] = Field(default=None, env="DISCORD_WEBHOOK_URL")
    
    # Trading Parameters
    paper_trading_enabled: bool = Field(default=True, env="PAPER_TRADING_ENABLED")
    max_positions: int = Field(default=10, env="MAX_POSITIONS")
    risk_per_trade: float = Field(default=0.02, env="RISK_PER_TRADE")  # 2%
    
    # Market Data Configuration
    update_interval: int = Field(default=10, env="UPDATE_INTERVAL")  # 10 detik
    websocket_reconnect_interval: int = Field(default=5, env="WEBSOCKET_RECONNECT_INTERVAL")
    
    # Signal Generation
    min_confidence_score: float = Field(default=70.0, env="MIN_CONFIDENCE_SCORE")
    signal_expiry_hours: int = Field(default=24, env="SIGNAL_EXPIRY_HOURS")
    
    # Risk Management
    max_daily_loss: float = Field(default=0.05, env="MAX_DAILY_LOSS")  # 5%
    stop_loss_multiplier: float = Field(default=2.0, env="STOP_LOSS_MULTIPLIER")
    
    # Supported Markets
    indonesia_stocks: List[str] = Field(default=[
        "BBCA.JK", "BBRI.JK", "BMRI.JK", "TLKM.JK", "ASII.JK",
        "UNVR.JK", "ICBP.JK", "HMSP.JK", "PGAS.JK", "ADRO.JK",
        "PTBA.JK", "ANTM.JK", "INCO.JK", "TINS.JK", "AKRA.JK",
        "MEDC.JK", "ITMG.JK", "AALI.JK", "LSIP.JK", "GGRM.JK",
        "HMSP.JK", "GOTO.JK", "AMRT.JK", "ACES.JK", "ADHI.JK",
        "AKRA.JK", "ANTM.JK", "ASII.JK", "BBCA.JK", "BBNI.JK",
        "BBRI.JK", "BBTN.JK", "BMRI.JK", "BRIS.JK", "BSDE.JK",
        "CPIN.JK", "CTRA.JK", "DMAS.JK", "ELSA.JK", "EXCL.JK",
        "GGRM.JK", "HMSP.JK", "ICBP.JK", "INCO.JK", "INDF.JK",
        "INKP.JK", "INTP.JK", "ITMG.JK", "JPFA.JK", "JSMR.JK",
        "KLBF.JK", "LPPF.JK", "LSIP.JK", "MEDC.JK", "MIKA.JK",
        "MLPL.JK", "MNCN.JK", "PGAS.JK", "PNBN.JK", "PNLF.JK",
        "POWL.JK", "PTBA.JK", "PTPP.JK", "PWON.JK", "SCMA.JK",
        "SIDO.JK", "SMGR.JK", "SMRA.JK", "SRTG.JK", "SSIA.JK",
        "TINS.JK", "TKIM.JK", "TLKM.JK", "TOWR.JK", "UNTR.JK",
        "UNVR.JK", "WIKA.JK", "WSKT.JK", "YULE.JK"
    ])
    
    us_stocks: List[str] = Field(default=[
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "AMD", "INTC",
        "CRM", "ADBE", "PYPL", "UBER", "LYFT", "COIN", "HOOD", "SOFI", "RIVN", "LCID",
        "NIO", "BABA", "JD", "PDD", "BILI", "DIDI", "ZM", "PTON", "DOCU", "SNOW",
        "PLTR", "RBLX", "ABNB", "PINS", "SNAP", "TWTR", "SPOT", "SQ", "SHOP", "NET",
        "DDOG", "MDB", "OKTA", "TWLO", "ROKU", "CRWD", "ZS", "OKTA", "SNOW", "PLTR"
    ])
    
    crypto_symbols: List[str] = Field(default=[
        "BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT",
        "LINKUSDT", "MATICUSDT", "UNIUSDT", "AVAXUSDT", "ATOMUSDT",
        "XLMUSDT", "VETUSDT", "FILUSDT", "TRXUSDT", "ETCUSDT",
        "XRPUSDT", "BCHUSDT", "LTCUSDT", "BNBUSDT", "DOGEUSDT",
        "SHIBUSDT", "MATICUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT"
    ])
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Instance settings global
settings = Settings()

# Utility functions
def get_database_url() -> str:
    """Mendapatkan URL database"""
    return settings.database_url


def get_redis_url() -> str:
    """Mendapatkan URL Redis"""
    return settings.redis_url


def is_production() -> bool:
    """Cek apakah environment adalah production"""
    return settings.environment == "production"


def get_supported_symbols() -> dict:
    """Mendapatkan semua symbol yang didukung"""
    return {
        "indonesia": settings.indonesia_stocks,
        "us": settings.us_stocks,
        "crypto": settings.crypto_symbols
    }


def get_risk_parameters() -> dict:
    """Mendapatkan parameter risk management"""
    return {
        "max_positions": settings.max_positions,
        "risk_per_trade": settings.risk_per_trade,
        "max_daily_loss": settings.max_daily_loss,
        "stop_loss_multiplier": settings.stop_loss_multiplier
    }