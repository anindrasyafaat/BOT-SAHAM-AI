"""
Trading Signals Models untuk Trading Command Center
Models untuk menyimpan trading signals dan performance metrics
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, Numeric, Boolean, Text, Enum
from sqlalchemy.sql import func
from database.connection import Base
from datetime import datetime
import enum


class SignalType(str, enum.Enum):
    """Enum untuk tipe signal"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class SignalStatus(str, enum.Enum):
    """Enum untuk status signal"""
    ACTIVE = "ACTIVE"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"
    STOPPED_OUT = "STOPPED_OUT"
    TARGET_HIT = "TARGET_HIT"


class TimeFrame(str, enum.Enum):
    """Enum untuk timeframe trading"""
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"
    H1 = "1h"
    H4 = "4h"
    D1 = "1d"
    W1 = "1w"


class TradingSignal(Base):
    """Model untuk trading signals"""
    
    __tablename__ = "trading_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    signal_type = Column(Enum(SignalType), nullable=False, index=True)
    
    # Signal details
    strategy_name = Column(String(100), nullable=False, index=True)
    timeframe = Column(Enum(TimeFrame), nullable=False)
    confidence_score = Column(Numeric(5, 2), nullable=False)  # 0-100%
    
    # Price levels
    entry_price = Column(Numeric(15, 4), nullable=False)
    target_price_1 = Column(Numeric(15, 4), nullable=True)
    target_price_2 = Column(Numeric(15, 4), nullable=True)
    target_price_3 = Column(Numeric(15, 4), nullable=True)
    stop_loss = Column(Numeric(15, 4), nullable=False)
    
    # Risk metrics
    risk_reward_ratio = Column(Numeric(8, 4), nullable=True)
    position_size = Column(Numeric(15, 4), nullable=True)
    max_loss = Column(Numeric(15, 4), nullable=True)
    
    # Analysis
    technical_analysis = Column(Text, nullable=True)
    fundamental_analysis = Column(Text, nullable=True)
    sentiment_analysis = Column(Text, nullable=True)
    
    # Signal metadata
    status = Column(Enum(SignalStatus), default=SignalStatus.ACTIVE, index=True)
    generated_at = Column(DateTime, default=func.now(), index=True)
    expires_at = Column(DateTime, nullable=True, index=True)
    
    # Performance tracking
    executed_at = Column(DateTime, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    pnl_amount = Column(Numeric(15, 4), nullable=True)
    pnl_percent = Column(Numeric(8, 4), nullable=True)
    
    # Validation
    is_valid = Column(Boolean, default=True)
    validation_notes = Column(Text, nullable=True)
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        return {
            "id": self.id,
            "symbol": self.symbol,
            "signal_type": self.signal_type.value,
            "strategy_name": self.strategy_name,
            "timeframe": self.timeframe.value,
            "confidence_score": float(self.confidence_score),
            "entry_price": float(self.entry_price),
            "target_price_1": float(self.target_price_1) if self.target_price_1 else None,
            "target_price_2": float(self.target_price_2) if self.target_price_2 else None,
            "target_price_3": float(self.target_price_3) if self.target_price_3 else None,
            "stop_loss": float(self.stop_loss),
            "risk_reward_ratio": float(self.risk_reward_ratio) if self.risk_reward_ratio else None,
            "position_size": float(self.position_size) if self.position_size else None,
            "max_loss": float(self.max_loss) if self.max_loss else None,
            "technical_analysis": self.technical_analysis,
            "fundamental_analysis": self.fundamental_analysis,
            "sentiment_analysis": self.sentiment_analysis,
            "status": self.status.value,
            "generated_at": self.generated_at.isoformat() if self.generated_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "pnl_amount": float(self.pnl_amount) if self.pnl_amount else None,
            "pnl_percent": float(self.pnl_percent) if self.pnl_percent else None,
            "is_valid": self.is_valid,
            "validation_notes": self.validation_notes,
        }


class SignalPerformance(Base):
    """Model untuk tracking performance signals"""
    
    __tablename__ = "signal_performance"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(100), nullable=False, index=True)
    symbol = Column(String(50), nullable=False, index=True)
    
    # Performance metrics
    total_signals = Column(Integer, default=0)
    winning_signals = Column(Integer, default=0)
    losing_signals = Column(Integer, default=0)
    
    win_rate = Column(Numeric(5, 2), nullable=True)  # Percentage
    avg_profit = Column(Numeric(8, 4), nullable=True)
    avg_loss = Column(Numeric(8, 4), nullable=True)
    profit_factor = Column(Numeric(8, 4), nullable=True)
    
    # Risk metrics
    max_drawdown = Column(Numeric(8, 4), nullable=True)
    sharpe_ratio = Column(Numeric(8, 4), nullable=True)
    max_consecutive_loss = Column(Integer, default=0)
    
    # Time-based stats
    period_start = Column(DateTime, nullable=False, index=True)
    period_end = Column(DateTime, nullable=True, index=True)
    
    # Metadata
    last_updated = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        return {
            "id": self.id,
            "strategy_name": self.strategy_name,
            "symbol": self.symbol,
            "total_signals": self.total_signals,
            "winning_signals": self.winning_signals,
            "losing_signals": self.losing_signals,
            "win_rate": float(self.win_rate) if self.win_rate else None,
            "avg_profit": float(self.avg_profit) if self.avg_profit else None,
            "avg_loss": float(self.avg_loss) if self.avg_loss else None,
            "profit_factor": float(self.profit_factor) if self.profit_factor else None,
            "max_drawdown": float(self.max_drawdown) if self.max_drawdown else None,
            "sharpe_ratio": float(self.sharpe_ratio) if self.sharpe_ratio else None,
            "max_consecutive_loss": self.max_consecutive_loss,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


class StrategyConfig(Base):
    """Model untuk konfigurasi strategy"""
    
    __tablename__ = "strategy_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    strategy_name = Column(String(100), nullable=False, unique=True, index=True)
    
    # Strategy parameters
    parameters = Column(Text, nullable=True)  # JSON string
    enabled = Column(Boolean, default=True)
    
    # Risk parameters
    max_positions = Column(Integer, default=5)
    risk_per_trade = Column(Numeric(5, 4), default=0.02)  # 2%
    min_confidence = Column(Numeric(5, 2), default=70.0)  # 70%
    
    # Time settings
    trading_hours_only = Column(Boolean, default=True)
    min_time_between_signals = Column(Integer, default=3600)  # seconds
    
    # Metadata
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    def to_dict(self) -> dict:
        """Convert model ke dictionary"""
        import json
        
        return {
            "id": self.id,
            "strategy_name": self.strategy_name,
            "parameters": json.loads(self.parameters) if self.parameters else {},
            "enabled": self.enabled,
            "max_positions": self.max_positions,
            "risk_per_trade": float(self.risk_per_trade),
            "min_confidence": float(self.min_confidence),
            "trading_hours_only": self.trading_hours_only,
            "min_time_between_signals": self.min_time_between_signals,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }