"""
Model paper trading: posisi terbuka dan riwayat transaksi.
Kas tidak disimpan terpisah: dihitung dari modal awal + arus kas semua transaksi.
"""

from sqlalchemy import Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from database.connection import Base


class Position(Base):
    __tablename__ = "positions"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, unique=True, index=True)
    quantity = Column(Float, nullable=False)
    avg_entry_price = Column(Float, nullable=False)  # mata uang asli simbol
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    signal_id = Column(Integer, nullable=True)
    opened_at = Column(DateTime, default=func.now())

    def to_dict(self) -> dict:
        return {
            "symbol": self.symbol, "quantity": self.quantity, "avg_entry_price": self.avg_entry_price,
            "stop_loss": self.stop_loss, "take_profit": self.take_profit, "signal_id": self.signal_id,
            "entry_date": self.opened_at.isoformat() if self.opened_at else None,
        }


class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    symbol = Column(String(50), nullable=False, index=True)
    side = Column(String(4), nullable=False)  # BUY / SELL
    quantity = Column(Float, nullable=False)
    price = Column(Float, nullable=False)       # mata uang asli
    fx_to_idr = Column(Float, nullable=False)   # kurs saat eksekusi
    fees_idr = Column(Float, nullable=False)
    realized_pnl_idr = Column(Float, nullable=True)  # hanya SELL
    reason = Column(String(50), nullable=True)       # manual / signal / stop_loss / take_profit
    signal_id = Column(Integer, nullable=True)
    executed_at = Column(DateTime, default=func.now(), index=True)

    @property
    def value_idr(self) -> float:
        return self.quantity * self.price * self.fx_to_idr

    def to_dict(self) -> dict:
        return {
            "id": self.id, "symbol": self.symbol, "side": self.side, "quantity": self.quantity,
            "price": self.price, "value_idr": self.value_idr, "fees": self.fees_idr,
            "realized_pnl": self.realized_pnl_idr, "reason": self.reason, "signal_id": self.signal_id,
            "trade_date": self.executed_at.isoformat() if self.executed_at else None,
        }
