"""
Signals Routes untuk Trading Command Center
API endpoints untuk trading signals dan performance
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from database.connection import get_db_session
from models.signals import TradingSignal, SignalPerformance, SignalType, SignalStatus
from utils.logger import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/")
async def get_active_signals(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    strategy: Optional[str] = Query(None, description="Filter by strategy"),
    min_confidence: Optional[float] = Query(None, ge=0, le=100, description="Minimum confidence score"),
    limit: int = Query(50, ge=1, le=200, description="Number of signals to return"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get active trading signals"""
    try:
        stmt = select(TradingSignal).where(TradingSignal.status == SignalStatus.ACTIVE)
        
        # Apply filters
        if symbol:
            stmt = stmt.where(TradingSignal.symbol == symbol)
        if strategy:
            stmt = stmt.where(TradingSignal.strategy_name == strategy)
        if min_confidence:
            stmt = stmt.where(TradingSignal.confidence_score >= min_confidence)
            
        stmt = stmt.order_by(desc(TradingSignal.generated_at)).limit(limit)
        
        result = await session.execute(stmt)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "data": [signal.to_dict() for signal in signals],
            "total": len(signals),
            "filters": {
                "symbol": symbol,
                "strategy": strategy,
                "min_confidence": min_confidence
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting active signals: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/history")
async def get_signal_history(
    symbol: Optional[str] = Query(None),
    strategy: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    status: Optional[str] = Query(None, description="Filter by signal status"),
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session)
):
    """Get historical trading signals"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stmt = select(TradingSignal).where(TradingSignal.generated_at >= cutoff_date)
        
        if symbol:
            stmt = stmt.where(TradingSignal.symbol == symbol)
        if strategy:
            stmt = stmt.where(TradingSignal.strategy_name == strategy)
        if status:
            stmt = stmt.where(TradingSignal.status == status)
            
        stmt = stmt.order_by(desc(TradingSignal.generated_at)).limit(limit)
        
        result = await session.execute(stmt)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "data": [signal.to_dict() for signal in signals],
            "total": len(signals),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting signal history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/performance")
async def get_strategy_performance(
    strategy: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session)
):
    """Get strategy performance metrics"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get performance records
        stmt = select(SignalPerformance).where(
            SignalPerformance.period_start >= cutoff_date
        )
        
        if strategy:
            stmt = stmt.where(SignalPerformance.strategy_name == strategy)
            
        result = await session.execute(stmt)
        performances = result.scalars().all()
        
        # Calculate overall statistics
        total_signals = sum(p.total_signals for p in performances)
        total_winning = sum(p.winning_signals for p in performances)
        total_losing = sum(p.losing_signals for p in performances)
        
        overall_win_rate = (total_winning / total_signals * 100) if total_signals > 0 else 0
        
        return {
            "status": "success",
            "data": {
                "strategies": [p.to_dict() for p in performances],
                "overall": {
                    "total_signals": total_signals,
                    "total_winning": total_winning,
                    "total_losing": total_losing,
                    "win_rate": overall_win_rate,
                    "period_days": days
                }
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting strategy performance: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/brain")
async def get_brain(request: Request, session: AsyncSession = Depends(get_db_session)):
    """Status AI Brain: parameter tiap strategi hasil belajar, performanya, dan jejak keputusan."""
    try:
        from models.signals import StrategyConfig
        configs = (await session.execute(select(StrategyConfig))).scalars().all()
        perf = {p.strategy_name: p.to_dict() for p in (await session.execute(select(SignalPerformance))).scalars().all()}
        gen = getattr(request.app.state, "signal_generator", None)
        return {
            "status": "success",
            "data": {
                "strategies": [{**c.to_dict(), "performance": perf.get(c.strategy_name)} for c in configs],
                "log": list(gen.brain_log) if gen else [],
            },
        }
    except Exception as e:
        logger.error(f"❌ Error getting brain state: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/strategies")
async def get_strategies(
    enabled_only: bool = Query(False, description="Show only enabled strategies"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get available trading strategies"""
    try:
        from models.signals import StrategyConfig
        
        stmt = select(StrategyConfig)
        if enabled_only:
            stmt = stmt.where(StrategyConfig.enabled == True)
            
        result = await session.execute(stmt)
        strategies = result.scalars().all()
        
        return {
            "status": "success",
            "data": [strategy.to_dict() for strategy in strategies],
            "total": len(strategies)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/strategies/{strategy_name}/toggle")
async def toggle_strategy(
    strategy_name: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session)
):
    """Enable/disable a trading strategy"""
    try:
        from models.signals import StrategyConfig
        
        # Get strategy config
        stmt = select(StrategyConfig).where(
            StrategyConfig.strategy_name == strategy_name
        )
        result = await session.execute(stmt)
        strategy = result.scalar_one_or_none()
        
        if not strategy:
            raise HTTPException(status_code=404, detail="Strategy not found")
            
        # Toggle enabled status
        strategy.enabled = not strategy.enabled
        await session.commit()
        await session.refresh(strategy)  # updated_at di-expire oleh onupdate; muat ulang secara async
        gen = getattr(request.app.state, "signal_generator", None)
        if gen:
            gen.strategy_configs[strategy_name] = strategy.to_dict()
        
        return {
            "status": "success",
            "message": f"Strategy {strategy_name} {'enabled' if strategy.enabled else 'disabled'}",
            "data": strategy.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error toggling strategy {strategy_name}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/winners")
async def get_winning_signals(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Get winning signals (profitable trades)"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stmt = select(TradingSignal).where(
            TradingSignal.closed_at >= cutoff_date,
            TradingSignal.pnl_percent > 0
        ).order_by(desc(TradingSignal.pnl_percent)).limit(limit)
        
        result = await session.execute(stmt)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "data": [signal.to_dict() for signal in signals],
            "total": len(signals),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting winning signals: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/losers")
async def get_losing_signals(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Get losing signals (unprofitable trades)"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        stmt = select(TradingSignal).where(
            TradingSignal.closed_at >= cutoff_date,
            TradingSignal.pnl_percent < 0
        ).order_by(TradingSignal.pnl_percent).limit(limit)
        
        result = await session.execute(stmt)
        signals = result.scalars().all()
        
        return {
            "status": "success",
            "data": [signal.to_dict() for signal in signals],
            "total": len(signals),
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting losing signals: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_signal_statistics(
    days: int = Query(30, ge=1, le=365),
    session: AsyncSession = Depends(get_db_session)
):
    """Get comprehensive signal statistics"""
    try:
        from datetime import datetime, timedelta
        
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all signals in period
        stmt = select(TradingSignal).where(
            TradingSignal.generated_at >= cutoff_date
        )
        result = await session.execute(stmt)
        signals = result.scalars().all()
        
        if not signals:
            return {
                "status": "success",
                "data": {
                    "total_signals": 0,
                    "win_rate": 0,
                    "avg_profit": 0,
                    "avg_loss": 0,
                    "profit_factor": 0,
                    "max_drawdown": 0,
                    "sharpe_ratio": 0
                },
                "period_days": days
            }
            
        # Calculate statistics
        total_signals = len(signals)
        winning_signals = [s for s in signals if s.pnl_percent and s.pnl_percent > 0]
        losing_signals = [s for s in signals if s.pnl_percent and s.pnl_percent < 0]
        
        win_rate = len(winning_signals) / total_signals * 100 if total_signals > 0 else 0
        
        avg_profit = sum(s.pnl_percent for s in winning_signals) / len(winning_signals) if winning_signals else 0
        avg_loss = abs(sum(s.pnl_percent for s in losing_signals) / len(losing_signals)) if losing_signals else 0
        
        profit_factor = avg_profit / avg_loss if avg_loss > 0 else 0
        
        # Calculate max drawdown (simplified)
        pnl_values = [s.pnl_percent or 0 for s in signals if s.pnl_percent]
        max_drawdown = 0
        peak = 0
        running_pnl = 0
        
        for pnl in pnl_values:
            running_pnl += pnl
            if running_pnl > peak:
                peak = running_pnl
            drawdown = peak - running_pnl
            if drawdown > max_drawdown:
                max_drawdown = drawdown
        
        # Calculate Sharpe ratio (simplified)
        if len(pnl_values) > 1:
            import statistics
            avg_return = sum(pnl_values) / len(pnl_values)
            std_dev = statistics.stdev(pnl_values) if len(pnl_values) > 1 else 0
            sharpe_ratio = avg_return / std_dev if std_dev > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            "status": "success",
            "data": {
                "total_signals": total_signals,
                "winning_signals": len(winning_signals),
                "losing_signals": len(losing_signals),
                "win_rate": win_rate,
                "avg_profit": avg_profit,
                "avg_loss": avg_loss,
                "profit_factor": profit_factor,
                "max_drawdown": max_drawdown,
                "sharpe_ratio": sharpe_ratio
            },
            "period_days": days
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting signal statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")