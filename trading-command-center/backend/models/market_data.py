"""
Market Data Models untuk Trading Command Center
Models untuk menyimpan market data real-time dan historical
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Boolean, Index
from sqlalchemy.sql import func
from database.connection import Base
from datetime import datetime


class MarketData(Base):
    """Model untuk menyimpan real-time market data"""
    
    __tablename__ = "market_data"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    
    # Price data
    current_price = Column(Numeric(15, 4), nullable=False)
    open_price = Column(Numeric(15, 4), nullable=False)
    high_price = Column(Numeric(15, 4), nullable=False)
    low_price = Column(Numeric(15, 4), nullable=False)
    close_price = Column(Numeric(15, 4), nullable=False)
    
    # Volume data
    volume = Column(Numeric(20, 2), nullable=True)
    volume_avg = Column(Numeric(20, 2), nullable=True)
    
    # Market metrics
    market_cap = Column(Numeric(20, 2), nullable=True)
    pe_ratio = Column(Numeric(10, 2), nullable=True)
    pb_ratio = Column(Numeric(10, 2), nullable=True)
    dividend_yield = Column(Numeric(6, 2), nullable=True)
    
    # Change data
    change_amount = Column(Numeric(15, 4), nullable=False)
    change_percent = Column(Numeric(8, 4), nullable=False)
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now(), index=True)
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Market info
    market_type = Column(String(20), nullable=False)  # stock, crypto, forex
    exchange = Column(String(50), nullable=True)
    currency = Column(String(10), nullable=True)
    
    # Additional metrics
    day_high = Column(Numeric(15, 4), nullable=True)
    day_low = Column(Numeric(15, 4), nullable=True)
    fifty_two_week_high = Column(Numeric(15, 4), nullable=True)
    fifty_two_week_low = Column(Numeric(15, 4), nullable=True)
    
    # Indexes untuk performance
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
        Index('idx_market_type', 'market_type'),
        Index('idx_last_updated', 'last_updated'),
    )
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "name": self.name,
            "current_price": float(self.current_price),
            "open_price": float(self.open_price),
            "high_price": float(self.high_price),
            "low_price": float(self.low_price),
            "close_price": float(self.close_price),
            "volume": float(self.volume) if self.volume else None,
            "volume_avg": float(self.volume_avg) if self.volume_avg else None,
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "pe_ratio": float(self.pe_ratio) if self.pe_ratio else None,
            "pb_ratio": float(self.pb_ratio) if self.pb_ratio else None,
            "dividend_yield": float(self.dividend_yield) if self.dividend_yield else None,
            "change_amount": float(self.change_amount),
            "change_percent": float(self.change_percent),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "market_type": self.market_type,
            "exchange": self.exchange,
            "currency": self.currency,
            "day_high": float(self.day_high) if self.day_high else None,
            "day_low": float(self.day_low) if self.day_low else None,
            "fifty_two_week_high": float(self.fifty_two_week_high) if self.fifty_two_week_high else None,
            "fifty_two_week_low": float(self.fifty_two_week_low) if self.fifty_two_week_low else None,
        }


class MarketSummary(Base):
    """Model untuk menyimpan market summary dan breadth data"""
    
    __tablename__ = "market_summary"
    
    id = Column(Integer, primary_key=True, index=True)
    market_type = Column(String(20), nullable=False, index=True)  # indonesia, us, crypto
    
    # Market breadth
    total_stocks = Column(Integer, nullable=False)
    advancers = Column(Integer, nullable=False)
    decliners = Column(Integer, nullable=False)
    unchanged = Column(Integer, nullable=False)
    
    # Market indices
    composite_index = Column(String(50), nullable=True)
    index_value = Column(Numeric(15, 4), nullable=True)
    index_change = Column(Numeric(15, 4), nullable=True)
    index_change_percent = Column(Numeric(8, 4), nullable=True)
    
    # Sector performance
    top_sector = Column(String(100), nullable=True)
    top_sector_change = Column(Numeric(8, 4), nullable=True)
    worst_sector = Column(String(100), nullable=True)
    worst_sector_change = Column(Numeric(8, 4), nullable=True)
    
    # Market sentiment
    fear_greed_index = Column(Numeric(6, 2), nullable=True)
    vix_level = Column(Numeric(8, 4), nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        return {
            "id": self.id,
            "market_type": self.market_type,
            "total_stocks": self.total_stocks,
            "advancers": self.advancers,
            "decliners": self.decliners,
            "unchanged": self.unchanged,
            "composite_index": self.composite_index,
            "index_value": float(self.index_value) if self.index_value else None,
            "index_change": float(self.index_change) if self.index_change else None,
            "index_change_percent": float(self.index_change_percent) if self.index_change_percent else None,
            "top_sector": self.top_sector,
            "top_sector_change": float(self.top_sector_change) if self.top_sector_change else None,
            "worst_sector": self.worst_sector,
            "worst_sector_change": float(self.worst_sector_change) if self.worst_sector_change else None,
            "fear_greed_index": float(self.fear_greed_index) if self.fear_greed_index else None,
            "vix_level": float(self.vix_level) if self.vix_level else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }


class SectorPerformance(Base):
    """Model untuk performance sektor"""
    
    __tablename__ = "sector_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    market_type = Column(String(20), nullable=False, index=True)
    sector_name = Column(String(100), nullable=False, index=True)
    
    # Performance metrics
    change_percent = Column(Numeric(8, 4), nullable=False)
    volume = Column(Numeric(20, 2), nullable=True)
    market_cap = Column(Numeric(20, 2), nullable=True)
    
    # Constituents
    total_stocks = Column(Integer, nullable=True)
    advancers = Column(Integer, nullable=True)
    decliners = Column(Integer, nullable=True)
    
    # Timestamps
    timestamp = Column(DateTime, default=func.now(), index=True)
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        return {
            "id": self.id,
            "market_type": self.market_type,
            "sector_name": self.sector_name,
            "change_percent": float(self.change_percent),
            "volume": float(self.volume) if self.volume else None,
            "market_cap": float(self.market_cap) if self.market_cap else None,
            "total_stocks": self.total_stocks,
            "advancers": self.advancers,
            "decliners": self.decliners,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }