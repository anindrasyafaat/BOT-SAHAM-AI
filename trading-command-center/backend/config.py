"""
Konfigurasi Trading Command Center
File konfigurasi utama untuk semua pengaturan aplikasi
"""

import os
from typing import Optional, List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Kelas konfigurasi utama untuk Trading Command Center"""
    
    # Environment
    environment: str = Field(default="development")
    debug: bool = Field(default=False)  # True membuka pesan error ke klien
    
    # Server Configuration
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)
    
    # Database
    database_url: str = Field(default="sqlite:///data/trading.db")
    
    # API Keys untuk Market Data
    
    # Notification Channels
    telegram_bot_token: Optional[str] = Field(default=None)
    telegram_chat_id: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)
    
    # Trading Parameters
    max_positions: int = Field(default=10)
    risk_per_trade: float = Field(default=0.02)  # 2%
    initial_capital: float = Field(default=100_000_000)  # IDR, modal paper trading
    buy_fee: float = Field(default=0.0015)    # 0.15% (rata-rata broker IDX)
    sell_fee: float = Field(default=0.0025)  # 0.25% termasuk PPh final 0.1%
    
    # Market Data Configuration
    update_interval: int = Field(default=60)  # detik
    
    # Signal Generation
    min_confidence_score: float = Field(default=70.0)
    signal_expiry_hours: int = Field(default=24)
    
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
        "PTBA.JK", "PTPP.JK", "PWON.JK", "SCMA.JK",
        "SIDO.JK", "SMGR.JK", "SMRA.JK", "SRTG.JK", "SSIA.JK",
        "TINS.JK", "TKIM.JK", "TLKM.JK", "TOWR.JK", "UNTR.JK",
        "UNVR.JK", "WIKA.JK", "YULE.JK"
    ])
    
    us_stocks: List[str] = Field(default=[
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "META", "NVDA", "NFLX", "AMD", "INTC",
        "CRM", "ADBE", "PYPL", "UBER", "LYFT", "COIN", "HOOD", "SOFI", "RIVN", "LCID",
        "NIO", "BABA", "JD", "PDD", "BILI", "ZM", "PTON", "DOCU", "SNOW",
        "PLTR", "RBLX", "ABNB", "PINS", "SNAP", "SPOT", "XYZ", "SHOP", "NET",
        "DDOG", "MDB", "OKTA", "TWLO", "ROKU", "CRWD", "ZS", "OKTA", "SNOW", "PLTR"
    ])
    
    crypto_symbols: List[str] = Field(default=[
        "BTCUSDT", "ETHUSDT", "ADAUSDT", "SOLUSDT", "DOTUSDT",
        "LINKUSDT", "POLUSDT", "AVAXUSDT", "ATOMUSDT",
        "XLMUSDT", "VETUSDT", "FILUSDT", "TRXUSDT", "ETCUSDT",
        "XRPUSDT", "BCHUSDT", "LTCUSDT", "BNBUSDT", "DOGEUSDT",
        "SHIBUSDT", "SANDUSDT", "MANAUSDT", "AXSUSDT"
    ])
    
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=False, extra="ignore")


# Instance settings global
settings = Settings()

# Utility functions
def get_database_url() -> str:
    """Mendapatkan URL database"""
    return settings.database_url


def get_supported_symbols() -> dict:
    """Mendapatkan semua symbol yang didukung"""
    return {
        "indonesia": settings.indonesia_stocks,
        "us": settings.us_stocks,
        "crypto": settings.crypto_symbols
    }
