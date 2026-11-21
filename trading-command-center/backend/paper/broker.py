"""
Paper broker: eksekusi beli/jual dengan harga pasar terakhir, fee, kas, P&L, kurva ekuitas,
dan auto-exit stop loss / take profit. Semua nilai agregat dalam IDR.
"""

import asyncio
import math
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database.connection import AsyncSessionLocal
from models.portfolio import Position, Trade
from utils.logger import setup_logging

logger = setup_logging()
IDX_LOT = 100
# Satu proses, satu buku kas: cek kas -> tulis transaksi harus atomik terhadap order lain yang bersamaan.
_book_lock = asyncio.Lock()


class BrokerError(ValueError):
    pass


def cash_from_trades(trades: List[Trade]) -> float:
    cash = settings.initial_capital
    for t in trades:
        cash += (-t.value_idr if t.side == "BUY" else t.value_idr) - t.fees_idr
    return cash


def _price_and_fx(mdm, symbol: str):
    quote = mdm.get_market_data(symbol)
    if not quote:
        raise BrokerError(f"Harga {symbol} belum tersedia")
    fx = mdm.to_idr(symbol)
    if fx is None:
        raise BrokerError("Kurs USD/IDR belum tersedia")
    return float(quote["current_price"]), fx


async def _all_trades(session: AsyncSession) -> List[Trade]:
    return list((await session.execute(select(Trade).order_by(Trade.executed_at, Trade.id))).scalars())


async def buy(session: AsyncSession, mdm, symbol: str, quantity: float, **kw) -> Trade:
    async with _book_lock:
        return await _buy(session, mdm, symbol, quantity, **kw)


async def sell(session: AsyncSession, mdm, symbol: str, quantity: Optional[float] = None, **kw) -> Trade:
    async with _book_lock:
        return await _sell(session, mdm, symbol, quantity, **kw)


async def _buy(session: AsyncSession, mdm, symbol: str, quantity: float, *, stop_loss=None,
               take_profit=None, signal_id=None, reason="manual") -> Trade:
    symbol = symbol.upper()
    if quantity <= 0:
        raise BrokerError("Jumlah harus > 0")
    if symbol.endswith(".JK") and quantity % IDX_LOT:
        raise BrokerError(f"Saham IDX harus kelipatan {IDX_LOT} lembar (1 lot)")
    price, fx = _price_and_fx(mdm, symbol)
    if stop_loss is not None and stop_loss >= price:
        raise BrokerError(f"Stop loss harus di bawah harga sekarang ({price:.4g})")
    if take_profit is not None and take_profit <= price:
        raise BrokerError(f"Take profit harus di atas harga sekarang ({price:.4g})")
    value = quantity * price * fx
    fee = value * settings.buy_fee
    cash = cash_from_trades(await _all_trades(session))
    if value + fee > cash:
        raise BrokerError(f"Kas tidak cukup: butuh {value + fee:,.0f} IDR, tersedia {cash:,.0f} IDR")

    pos = (await session.execute(select(Position).where(Position.symbol == symbol))).scalar_one_or_none()
    if pos is None:
        open_count = len((await session.execute(select(Position.id))).all())
        if open_count >= settings.max_positions:
            raise BrokerError(f"Maksimum {settings.max_positions} posisi terbuka")
        pos = Position(symbol=symbol, quantity=0, avg_entry_price=0)
        session.add(pos)
    pos.avg_entry_price = (pos.avg_entry_price * pos.quantity + price * quantity) / (pos.quantity + quantity)
    pos.quantity += quantity
    pos.stop_loss = stop_loss if stop_loss is not None else pos.stop_loss
    pos.take_profit = take_profit if take_profit is not None else pos.take_profit
    pos.signal_id = signal_id if signal_id is not None else pos.signal_id

    trade = Trade(symbol=symbol, side="BUY", quantity=quantity, price=price, fx_to_idr=fx,
                  fees_idr=fee, reason=reason, signal_id=signal_id, executed_at=datetime.now())
    session.add(trade)
    await session.commit()
    return trade


async def _sell(session: AsyncSession, mdm, symbol: str, quantity: Optional[float] = None, *, reason="manual") -> Trade:
    symbol = symbol.upper()
    pos = (await session.execute(select(Position).where(Position.symbol == symbol))).scalar_one_or_none()
    if pos is None:
        raise BrokerError(f"Tidak ada posisi {symbol}")
    quantity = pos.quantity if quantity is None else quantity
    if quantity <= 0 or quantity > pos.quantity:
        raise BrokerError(f"Jumlah jual harus 1..{pos.quantity:g}")
    if symbol.endswith(".JK") and quantity % IDX_LOT:
        raise BrokerError(f"Saham IDX harus kelipatan {IDX_LOT} lembar (1 lot)")
    price, fx = _price_and_fx(mdm, symbol)
    value = quantity * price * fx
    fee = value * settings.sell_fee
    # shortcut: P&L aset USD memakai kurs saat jual untuk modal juga, cukup untuk paper trading
    pnl = (price - pos.avg_entry_price) * quantity * fx - fee

    trade = Trade(symbol=symbol, side="SELL", quantity=quantity, price=price, fx_to_idr=fx, fees_idr=fee,
                  realized_pnl_idr=pnl, reason=reason, signal_id=pos.signal_id, executed_at=datetime.now())
    session.add(trade)
    pos.quantity -= quantity
    if pos.quantity <= 1e-9:
        await session.delete(pos)
    await session.commit()
    return trade


async def positions(session: AsyncSession, mdm) -> List[dict]:
    out = []
    for p in (await session.execute(select(Position).order_by(Position.symbol))).scalars():
        q = mdm.get_market_data(p.symbol) or {}
        price = q.get("current_price", p.avg_entry_price)
        fx = mdm.to_idr(p.symbol) or 0.0
        d = p.to_dict()
        d.update(
            name=q.get("name", p.symbol), current_price=price,
            market_value=p.quantity * price * fx,
            unrealized_pnl=(price - p.avg_entry_price) * p.quantity * fx,
            unrealized_pnl_percent=(price / p.avg_entry_price - 1) * 100 if p.avg_entry_price else 0.0,
            # posisi yang dibuka hari ini diukur dari harga beli, bukan penutupan kemarin
            today_pnl=(price - (p.avg_entry_price if p.opened_at and p.opened_at.date() == date.today()
                                else q.get("close_price", price))) * p.quantity * fx,
        )
        out.append(d)
    return out


async def summary(session: AsyncSession, mdm) -> dict:
    trades = await _all_trades(session)
    pos = await positions(session, mdm)
    cash = cash_from_trades(trades)
    invested = sum(p["market_value"] for p in pos)
    total = cash + invested
    today = sum(p["today_pnl"] for p in pos)
    return {
        "initial_capital": settings.initial_capital,
        "total_value": total, "cash_balance": cash, "total_invested": invested,
        "total_pnl": total - settings.initial_capital,
        "total_pnl_percent": (total / settings.initial_capital - 1) * 100,
        "positions_count": len(pos),
        "today_pnl": today, "today_pnl_percent": today / (total - today) * 100 if total - today else 0.0,
        "usd_idr": mdm.usd_idr,
    }


def _close_on(df, day: date) -> Optional[float]:
    closes = df["Close"]
    idx = [d.date() for d in closes.index]
    best = None
    for d, v in zip(idx, closes.values):
        if d <= day:
            best = float(v)
    return best


def equity_series(trades: List[Trade], history: Dict, to_idr, days: int = 90, today: Optional[date] = None) -> List[dict]:
    """Rekonstruksi nilai portofolio harian dari transaksi + harga penutupan historis."""
    today = today or date.today()
    start = today - timedelta(days=days - 1)
    first_trade = min((t.executed_at.date() for t in trades), default=today)
    start = max(start, first_trade) if trades else today
    out, prev = [], None
    for i in range((today - start).days + 1):
        day = start + timedelta(days=i)
        cash, qty = settings.initial_capital, {}
        for t in trades:
            if t.executed_at.date() > day:
                break
            sign = 1 if t.side == "BUY" else -1
            cash += -sign * t.value_idr - t.fees_idr
            qty[t.symbol] = qty.get(t.symbol, 0) + sign * t.quantity
        value = cash
        for sym, q in qty.items():
            if q > 1e-9 and sym in history:
                close = _close_on(history[sym], day)
                value += q * (close or 0) * (to_idr(sym) or 0)
        out.append({"date": day.isoformat(), "value": value,
                    "daily_return": (value / prev - 1) * 100 if prev else 0.0})
        prev = value
    return out


def performance(trades: List[Trade], equity: List[dict]) -> dict:
    sells = [t for t in trades if t.side == "SELL" and t.realized_pnl_idr is not None]
    wins = [t.realized_pnl_idr for t in sells if t.realized_pnl_idr > 0]
    losses = [t.realized_pnl_idr for t in sells if t.realized_pnl_idr <= 0]
    values = [e["value"] for e in equity]
    peak, mdd = -math.inf, 0.0
    for v in values:
        peak = max(peak, v)
        mdd = min(mdd, (v / peak - 1) * 100 if peak > 0 else 0.0)
    rets = [e["daily_return"] / 100 for e in equity[1:]]
    sharpe = None
    if len(rets) > 1:
        mean = sum(rets) / len(rets)
        sd = (sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)) ** 0.5
        sharpe = mean / sd * math.sqrt(252) if sd > 0 else None
    return {
        "total_return": (values[-1] / settings.initial_capital - 1) * 100 if values else 0.0,
        "max_drawdown": mdd,
        "sharpe_ratio": sharpe,
        "total_trades": len(trades),
        "closed_trades": len(sells),
        "win_rate": len(wins) / len(sells) * 100 if sells else None,
        "profit_factor": sum(wins) / abs(sum(losses)) if losses and sum(losses) else None,
        "avg_win": sum(wins) / len(wins) if wins else None,
        "avg_loss": sum(losses) / len(losses) if losses else None,
        "best_trade": max((t.realized_pnl_idr for t in sells), default=None),
        "worst_trade": min((t.realized_pnl_idr for t in sells), default=None),
    }


async def check_exits(mdm):
    """Tutup otomatis posisi yang menyentuh stop loss / take profit."""
    async with AsyncSessionLocal() as session:
        for p in list((await session.execute(select(Position))).scalars()):
            q = mdm.get_market_data(p.symbol)
            if not q:
                continue
            price = q["current_price"]
            reason = ("stop_loss" if p.stop_loss and price <= p.stop_loss
                      else "take_profit" if p.take_profit and price >= p.take_profit else None)
            if reason:
                try:
                    t = await sell(session, mdm, p.symbol, reason=reason)
                    logger.info(f"💼 Auto-exit {p.symbol} ({reason}) P&L {t.realized_pnl_idr:,.0f} IDR")
                    from notifications.manager import NotificationManager
                    await NotificationManager().notify(
                        "trade", f"{reason.replace('_', ' ').title()} {p.symbol}",
                        f"Dijual {t.quantity:g} @ {t.price:.4g}, P&L {t.realized_pnl_idr:,.0f} IDR", symbol=p.symbol)
                except BrokerError as e:
                    logger.warning(f"⚠️ Auto-exit {p.symbol} gagal: {e}")
