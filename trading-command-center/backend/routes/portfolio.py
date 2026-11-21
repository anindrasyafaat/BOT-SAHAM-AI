"""
Portfolio Routes untuk Trading Command Center (paper trading nyata, lihat paper/broker.py).
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import get_db_session
from models.portfolio import Trade
from models.signals import SignalType, TradingSignal
from paper import broker

router = APIRouter()


def _mdm(request: Request):
    mdm = getattr(request.app.state, "market_data_manager", None)
    if mdm is None:
        raise HTTPException(status_code=503, detail="Market data belum siap")
    return mdm


class ExecuteSignal(BaseModel):
    signal_id: int
    quantity: float = Field(gt=0)


class Order(BaseModel):
    symbol: str
    quantity: Optional[float] = Field(default=None, gt=0)
    stop_loss: Optional[float] = Field(default=None, gt=0)
    take_profit: Optional[float] = Field(default=None, gt=0)


@router.get("/")
async def get_portfolio_summary(request: Request, session: AsyncSession = Depends(get_db_session)):
    return {"status": "success", "data": await broker.summary(session, _mdm(request))}


@router.get("/positions")
async def get_positions(request: Request, session: AsyncSession = Depends(get_db_session)):
    data = await broker.positions(session, _mdm(request))
    return {"status": "success", "data": data, "total": len(data)}


@router.get("/trades")
async def get_trade_history(limit: int = Query(50, ge=1, le=500), offset: int = Query(0, ge=0),
                            session: AsyncSession = Depends(get_db_session)):
    rows = (await session.execute(
        select(Trade).order_by(desc(Trade.executed_at), desc(Trade.id)).offset(offset).limit(limit))).scalars()
    data = [t.to_dict() for t in rows]
    return {"status": "success", "data": data, "total": len(data)}


@router.get("/equity-curve")
async def get_equity_curve(request: Request, days: int = Query(90, ge=2, le=365),
                           session: AsyncSession = Depends(get_db_session)):
    mdm = _mdm(request)
    curve = broker.equity_series(await broker._all_trades(session), mdm.history, mdm.to_idr, days)
    return {"status": "success", "data": curve, "total_points": len(curve)}


@router.get("/performance")
async def get_portfolio_performance(request: Request, session: AsyncSession = Depends(get_db_session)):
    mdm = _mdm(request)
    trades = await broker._all_trades(session)
    return {"status": "success",
            "data": broker.performance(trades, broker.equity_series(trades, mdm.history, mdm.to_idr, 365))}


@router.post("/buy")
async def buy(order: Order, request: Request, session: AsyncSession = Depends(get_db_session)):
    if order.quantity is None:
        raise HTTPException(status_code=422, detail="quantity wajib")
    try:
        t = await broker.buy(session, _mdm(request), order.symbol, order.quantity,
                             stop_loss=order.stop_loss, take_profit=order.take_profit)
    except broker.BrokerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "data": t.to_dict()}


@router.post("/execute-signal")
async def execute_signal(body: ExecuteSignal, request: Request, session: AsyncSession = Depends(get_db_session)):
    sig = await session.get(TradingSignal, body.signal_id)
    if sig is None:
        raise HTTPException(status_code=404, detail="Sinyal tidak ditemukan")
    try:
        if sig.signal_type in (SignalType.BUY, SignalType.STRONG_BUY):
            t = await broker.buy(session, _mdm(request), sig.symbol, body.quantity,
                                 stop_loss=float(sig.stop_loss),
                                 take_profit=float(sig.target_price_1) if sig.target_price_1 else None,
                                 signal_id=sig.id, reason="signal")
        else:  # tanpa short selling: sinyal jual menutup posisi yang ada
            t = await broker.sell(session, _mdm(request), sig.symbol, body.quantity, reason="signal")
    except broker.BrokerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "message": "Sinyal dieksekusi (paper trading)", "data": t.to_dict()}


@router.post("/close-position")
async def close_position(order: Order, request: Request, session: AsyncSession = Depends(get_db_session)):
    try:
        t = await broker.sell(session, _mdm(request), order.symbol, order.quantity)
    except broker.BrokerError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"status": "success", "message": "Posisi ditutup", "data": t.to_dict()}
