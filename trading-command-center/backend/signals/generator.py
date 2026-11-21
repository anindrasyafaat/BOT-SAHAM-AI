"""
Signal Generator untuk Trading Command Center
Mengimplementasikan 12 strategi trading otomatis dengan AI
"""

import asyncio
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import pandas as pd
import numpy as np
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import AsyncSessionLocal
from models.signals import TradingSignal, SignalType, SignalStatus, TimeFrame, StrategyConfig
from market_data.manager import MarketDataManager
from strategies.technical import TechnicalStrategy
from strategies.fundamental import FundamentalStrategy
from strategies.sentiment import SentimentStrategy
from strategies.ml_ensemble import MLEnsembleStrategy
from signals.learning import adapt, evaluate_signal, valid_levels
from collections import deque
from config import settings, get_supported_symbols
from utils.logger import setup_logging

logger = setup_logging()


@dataclass
class SignalParameters:
    """Parameter untuk signal generation"""
    min_confidence: float = 70.0
    max_positions_per_strategy: int = 3
    risk_per_trade: float = 0.02
    min_risk_reward: float = 1.5
    signal_expiry_hours: int = 24


class SignalGenerator:
    """Generator untuk trading signals dengan multiple strategies"""
    
    def __init__(self, market_data_manager: MarketDataManager, websocket_manager):
        self.market_data_manager = market_data_manager
        self.websocket_manager = websocket_manager
        self.running = False
        
        # Strategy instances
        self.technical_strategy = TechnicalStrategy()
        self.fundamental_strategy = FundamentalStrategy()
        self.sentiment_strategy = SentimentStrategy()
        self.ml_strategy = MLEnsembleStrategy()
        
        # Signal tracking
        self.active_signals: Dict[str, List[TradingSignal]] = {}
        self.signal_history: Dict[str, List[dict]] = {}
        self.signal_cache: Dict[str, dict] = {}
        
        # Parameters
        self.parameters = SignalParameters(min_confidence=settings.min_confidence_score,
                                           signal_expiry_hours=settings.signal_expiry_hours)
        self.symbols = get_supported_symbols()
        
        # Rate limiting
        self.last_signal_time: Dict[str, datetime] = {}
        self.min_signal_interval = 300  # 5 menit

        # AI Brain: konfigurasi per strategi yang terus disesuaikan + jejak keputusannya
        self.strategy_configs: Dict[str, dict] = {}
        self.brain_log: deque = deque(maxlen=200)
        
    async def start(self):
        """Start signal generator"""
        logger.info("🚀 Starting Signal Generator...")
        
        self.running = True
        
        # Load strategy configurations
        await self._load_strategy_configs()
        
        # Start background tasks
        asyncio.create_task(self._signal_generation_loop())
        asyncio.create_task(self._signal_validation_loop())
        asyncio.create_task(self._performance_tracking_loop())
        
        logger.info("✅ Signal Generator started")
        
    async def stop(self):
        """Stop signal generator"""
        logger.info("🛑 Stopping Signal Generator...")
        self.running = False
        logger.info("✅ Signal Generator stopped")
        
    async def _load_strategy_configs(self):
        """Load strategy configurations dari database"""
        try:
            async with AsyncSessionLocal() as session:
                # Check if configs exist
                from sqlalchemy import select
                result = await session.execute(select(StrategyConfig))
                configs = result.scalars().all()
                
                if not configs:
                    # Create default configs
                    await self._create_default_configs(session)
                    configs = (await session.execute(select(StrategyConfig))).scalars().all()

                self.strategy_configs = {c.strategy_name: c.to_dict() for c in configs}

                recent = (await session.execute(
                    select(TradingSignal)
                    .where(TradingSignal.generated_at >= datetime.now() - timedelta(hours=self.parameters.signal_expiry_hours))
                    .order_by(TradingSignal.generated_at))).scalars().all()
                for sig in recent:  # cegah sinyal yang sama dibuat ulang setelah restart
                    self.signal_cache[f"{sig.symbol}_{sig.strategy_name}"] = sig.to_dict()
                active = (await session.execute(
                    select(TradingSignal).where(TradingSignal.status == SignalStatus.ACTIVE))).scalars().all()
                for sig in active:
                    self.active_signals.setdefault(sig.symbol, []).append(sig)
                logger.info(f"✅ {len(active)} sinyal aktif dimuat dari database")
                    
        except Exception as e:
            logger.error(f"❌ Error loading strategy configs: {e}")
            
    async def _create_default_configs(self, session: AsyncSession):
        """Create default strategy configurations"""
        try:
            default_configs = [
                StrategyConfig(
                    strategy_name="EMA_Crossover",
                    parameters='{"fast_ema": 8, "slow_ema": 21, "volume_threshold": 1.5}',
                    enabled=True,
                    min_confidence=75.0
                ),
                StrategyConfig(
                    strategy_name="SuperTrend_RSI",
                    parameters='{"atr_period": 10, "factor": 3.0, "rsi_period": 14}',
                    enabled=True,
                    min_confidence=70.0
                ),
                StrategyConfig(
                    strategy_name="Bollinger_MACD",
                    parameters='{"bb_period": 20, "bb_std": 2, "macd_fast": 12, "macd_slow": 26}',
                    enabled=True,
                    min_confidence=72.0
                ),
                StrategyConfig(
                    strategy_name="VWAP_OrderBlock",
                    parameters='{"vwap_period": 1, "ob_threshold": 0.02}',
                    enabled=True,
                    min_confidence=78.0
                ),
                StrategyConfig(
                    strategy_name="Breakout_Volume",
                    parameters='{"lookback_days": 52, "volume_multiplier": 2.0}',
                    enabled=True,
                    min_confidence=80.0
                ),
                StrategyConfig(
                    strategy_name="Mean_Reversion",
                    parameters='{"zscore_period": 20, "zscore_threshold": 2.0}',
                    enabled=True,
                    min_confidence=68.0
                ),
                StrategyConfig(
                    strategy_name="Liquidity_Sweep",
                    parameters='{"sweep_threshold": 0.01, "volume_spike": 3.0}',
                    enabled=True,
                    min_confidence=82.0
                ),
                StrategyConfig(
                    strategy_name="Golden_Cross",
                    parameters='{"fast_ma": 50, "slow_ma": 200, "volume_confirm": true}',
                    enabled=True,
                    min_confidence=85.0
                ),
                StrategyConfig(
                    strategy_name="Heikin_Ashi",
                    parameters='{"trend_period": 5, "volume_filter": true}',
                    enabled=True,
                    min_confidence=73.0
                ),
                StrategyConfig(
                    strategy_name="ML_Ensemble",
                    parameters='{"model_version": "v1.0", "features": ["price", "volume", "technical"]}',
                    enabled=True,
                    min_confidence=76.0
                ),
            ]
            
            for config in default_configs:
                session.add(config)
                
            await session.commit()
            logger.info("✅ Default strategy configs created")
            
        except Exception as e:
            logger.error(f"❌ Error creating default configs: {e}")
            
    async def _signal_generation_loop(self):
        """Main loop untuk signal generation"""
        while self.running:
            try:
                # Generate signals untuk semua symbols
                await self._generate_all_signals()
                
                # Wait sebelum next cycle
                await asyncio.sleep(60)  # Check setiap menit
                
            except Exception as e:
                logger.error(f"❌ Error in signal generation loop: {e}")
                await asyncio.sleep(30)
                
    async def _generate_all_signals(self):
        """Generate signals untuk semua symbols dan strategies"""
        try:
            # Get market data
            market_data = self.market_data_manager.get_all_market_data()
            
            if not market_data:
                logger.warning("⚠️ No market data available for signal generation")
                return
                
            if self.ml_strategy.needs_training() and self.market_data_manager.history:
                await asyncio.to_thread(self.ml_strategy.train, dict(self.market_data_manager.history))

            # Process setiap symbol
            for symbol, data in market_data.items():
                # Skip jika belum waktunya (rate limiting)
                if self._should_skip_signal(symbol):
                    continue
                    
                # Generate signals untuk symbol
                signals = await self._generate_symbol_signals(symbol, data)
                
                # Simpan dan broadcast signals
                for signal in signals:
                    await self._process_new_signal(signal)
                    
                # Update last signal time
                self.last_signal_time[symbol] = datetime.now()
                
        except Exception as e:
            logger.error(f"❌ Error generating all signals: {e}")
            
    async def _generate_symbol_signals(self, symbol: str, market_data: dict) -> List[TradingSignal]:
        """Generate signals untuk single symbol"""
        signals = []
        
        try:
            # Get historical data untuk analysis
            historical_data = await self.market_data_manager.get_historical_data(symbol, days=250)
            
            if not historical_data:
                return signals
                
            # Convert ke DataFrame
            df = self._create_dataframe(historical_data)
            
            # Generate signals dari setiap strategy
            strategy_signals = await asyncio.gather(
                self.technical_strategy.generate_signals(symbol, df, market_data),
                self.fundamental_strategy.generate_signals(symbol, market_data),
                self.sentiment_strategy.generate_signals(symbol, market_data),
                self.ml_strategy.generate_signals(symbol, df, market_data),
                return_exceptions=True
            )
            
            # Process strategy results
            for i, result in enumerate(strategy_signals):
                if isinstance(result, Exception):
                    logger.error(f"❌ Strategy {i} error for {symbol}: {result}")
                    continue
                if result:
                    signals.extend(result)
                    
        except Exception as e:
            logger.error(f"❌ Error generating signals for {symbol}: {e}")
            
        return signals
        
    def _create_dataframe(self, historical_data: List[dict]) -> pd.DataFrame:
        """Create pandas DataFrame dari historical data"""
        try:
            df = pd.DataFrame(historical_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            # Convert numeric columns
            numeric_cols = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
            for col in numeric_cols:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
                    
            return df.sort_index()
            
        except Exception as e:
            logger.error(f"❌ Error creating DataFrame: {e}")
            return pd.DataFrame()
            
    def _should_skip_signal(self, symbol: str) -> bool:
        """Check apakah harus skip signal generation untuk symbol"""
        if symbol not in self.last_signal_time:
            return False
            
        time_since_last = datetime.now() - self.last_signal_time[symbol]
        return time_since_last.total_seconds() < self.min_signal_interval
        
    async def _process_new_signal(self, signal: TradingSignal):
        """Process new signal"""
        try:
            # Validate signal
            if not await self._validate_signal(signal):
                return
                
            # Save ke database
            await self._save_signal(signal)
            
            # Add ke active signals
            if signal.symbol not in self.active_signals:
                self.active_signals[signal.symbol] = []
            self.active_signals[signal.symbol].append(signal)
            
            # Cache signal
            self.signal_cache[f"{signal.symbol}_{signal.strategy_name}"] = signal.to_dict()
            
            # Broadcast ke WebSocket
            await self.websocket_manager.broadcast({
                'type': 'new_signal',
                'signal': signal.to_dict()
            }, channel='signals')
            
            # Send notifications
            await self._send_signal_notification(signal)
            
            logger.info(f"🚀 New {signal.signal_type.value} signal for {signal.symbol} "
                       f"({signal.strategy_name}) - Confidence: {signal.confidence_score}%")
            
        except Exception as e:
            logger.error(f"❌ Error processing signal: {e}")
            
    async def _validate_signal(self, signal: TradingSignal) -> bool:
        """Validate signal sebelum diproses"""
        try:
            # Check confidence score
            if not valid_levels(signal.signal_type in (SignalType.BUY, SignalType.STRONG_BUY),
                                float(signal.entry_price), float(signal.stop_loss),
                                float(signal.target_price_1) if signal.target_price_1 else None):
                logger.warning(f"⚠️ Sinyal {signal.strategy_name} {signal.symbol} ditolak: level SL/TP tidak konsisten")
                return False
            cfg = self.strategy_configs.get(signal.strategy_name)
            if cfg and not cfg["enabled"]:
                return False
            min_conf = cfg["min_confidence"] if cfg else self.parameters.min_confidence
            if signal.confidence_score < min_conf:
                return False
                
            # Check risk reward ratio
            if signal.risk_reward_ratio and signal.risk_reward_ratio < self.parameters.min_risk_reward:
                return False
                
            # Check for duplicate signals
            cache_key = f"{signal.symbol}_{signal.strategy_name}"
            if cache_key in self.signal_cache:
                cached_signal = self.signal_cache[cache_key]
                if cached_signal['signal_type'] == signal.signal_type.value:
                    # Check if signal is too recent
                    time_diff = datetime.now() - datetime.fromisoformat(cached_signal['generated_at'])
                    if time_diff.total_seconds() < self.parameters.signal_expiry_hours * 3600:  # candle harian: satu sinyal per arah per masa berlaku
                        return False
                        
            return True
            
        except Exception as e:
            logger.error(f"❌ Error validating signal: {e}")
            return False
            
    async def _save_signal(self, signal: TradingSignal):
        """Save signal ke database"""
        try:
            async with AsyncSessionLocal() as session:
                session.add(signal)
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Error saving signal: {e}")
            
    async def _send_signal_notification(self, signal: TradingSignal):
        """Send signal notification"""
        try:
            # Format message
            message = self._format_signal_message(signal)
            
            # Send ke notification service
            from notifications.manager import NotificationManager
            notification_manager = NotificationManager()
            
            await notification_manager.send_signal_alert(signal, message)
            
        except Exception as e:
            logger.error(f"❌ Error sending notification: {e}")
            
    def _format_signal_message(self, signal: TradingSignal) -> str:
        """Format signal message untuk notification"""
        emoji = "🚀" if signal.signal_type in [SignalType.BUY, SignalType.STRONG_BUY] else "📉"
        
        message = f"""
{emoji} SIGNAL BARU - {signal.symbol}

Signal: {signal.signal_type.value}
Entry: {signal.entry_price}
TP1: {signal.target_price_1 or 'N/A'}
TP2: {signal.target_price_2 or 'N/A'}
SL: {signal.stop_loss}

Confidence: {signal.confidence_score}%
Strategy: {signal.strategy_name}
Timeframe: {signal.timeframe.value}

Risk/Reward: {signal.risk_reward_ratio or 'N/A'}
        """
        
        return message.strip()
        
    async def _signal_validation_loop(self):
        """Loop untuk validasi dan update signals"""
        while self.running:
            try:
                await self._validate_active_signals()
                await asyncio.sleep(30)  # Check setiap 30 detik
                
            except Exception as e:
                logger.error(f"❌ Error in signal validation loop: {e}")
                await asyncio.sleep(10)
                
    async def _validate_active_signals(self):
        """Tutup sinyal yang kena SL/TP atau kedaluwarsa; P&L dari sisi arah sinyal (lihat learning.evaluate_signal)."""
        try:
            now = datetime.now()
            for symbol, signals in self.active_signals.items():
                quote = self.market_data_manager.get_market_data(symbol)
                still_active = []
                for signal in signals:
                    try:
                        expired = bool(signal.expires_at and now > signal.expires_at)
                        if not quote:
                            if expired:  # tanpa harga: tutup tanpa P&L
                                signal.status, signal.closed_at = SignalStatus.EXPIRED, now
                                await self._update_signal_status(signal)
                            else:
                                still_active.append(signal)
                            continue
                        price, entry = float(quote["current_price"]), float(signal.entry_price)
                        status, pnl = evaluate_signal(
                            signal.signal_type in (SignalType.BUY, SignalType.STRONG_BUY), entry,
                            float(signal.stop_loss), float(signal.target_price_1) if signal.target_price_1 else None,
                            price, expired)
                        if status is None:
                            still_active.append(signal)
                            continue
                        signal.status, signal.closed_at = SignalStatus(status), now
                        signal.pnl_percent = pnl
                        signal.pnl_amount = entry * pnl / 100
                        await self._update_signal_status(signal)
                    except Exception as e:  # satu sinyal rusak tidak boleh menghentikan penutupan sinyal lain
                        logger.error(f"❌ Error validating signal {signal.id} {symbol}: {e}")
                        still_active.append(signal)
                self.active_signals[symbol] = still_active
        except Exception as e:
            logger.error(f"❌ Error validating signals: {e}")

    async def _update_signal_status(self, signal: TradingSignal):
        """Update signal status di database"""
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select
                
                stmt = select(TradingSignal).where(TradingSignal.id == signal.id)
                result = await session.execute(stmt)
                db_signal = result.scalar_one_or_none()
                
                if db_signal:
                    db_signal.status = signal.status
                    db_signal.closed_at = signal.closed_at
                    db_signal.pnl_amount = signal.pnl_amount
                    db_signal.pnl_percent = signal.pnl_percent
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"❌ Error updating signal status: {e}")
            
    async def _performance_tracking_loop(self):
        """Loop untuk performance tracking"""
        while self.running:
            try:
                await self._update_performance_metrics()
                await asyncio.sleep(300)  # Update setiap 5 menit
                
            except Exception as e:
                logger.error(f"❌ Error in performance tracking loop: {e}")
                await asyncio.sleep(30)
                
    async def _update_performance_metrics(self):
        """Update performance metrics untuk strategies"""
        try:
            # Calculate performance untuk setiap strategy
            from sqlalchemy import select
            async with AsyncSessionLocal() as session:
                names = set((await session.execute(select(TradingSignal.strategy_name).distinct())).scalars())
            for strategy in sorted(names | set(self.strategy_configs)):
                await self._calculate_strategy_performance(strategy)

            # Fitur Generate: lengkapi konteks pengalaman sinyal & nilai keputusan yang sudah jatuh tempo
            from insight.service import ensure_contexts, evaluate_due
            await ensure_contexts(self.market_data_manager)
            await evaluate_due(self.market_data_manager)
                
        except Exception as e:
            logger.error(f"❌ Error updating performance metrics: {e}")
            
    async def _calculate_strategy_performance(self, strategy_name: str):
        """Calculate performance metrics untuk strategy"""
        try:
            async with AsyncSessionLocal() as session:
                from sqlalchemy import select, func
                from models.signals import SignalPerformance
                
                # Get recent signals untuk strategy
                stmt = (
                    select(TradingSignal)
                    .where(TradingSignal.strategy_name == strategy_name)
                    .where(TradingSignal.generated_at >= datetime.now() - timedelta(days=30))
                )
                
                result = await session.execute(stmt)
                signals = result.scalars().all()
                
                if not signals:
                    return
                    
                # Calculate metrics
                total_signals = len(signals)
                winning_signals = len([s for s in signals if s.pnl_percent and s.pnl_percent > 0])
                losing_signals = len([s for s in signals if s.pnl_percent and s.pnl_percent < 0])
                
                closed = winning_signals + losing_signals
                win_rate = (winning_signals / closed * 100) if closed > 0 else 0
                
                # Calculate average profit/loss
                profits = [s.pnl_percent for s in signals if s.pnl_percent and s.pnl_percent > 0]
                losses = [s.pnl_percent for s in signals if s.pnl_percent and s.pnl_percent < 0]
                
                avg_profit = np.mean(profits) if profits else 0
                avg_loss = np.mean(losses) if losses else 0
                profit_factor = abs(avg_profit / avg_loss) if avg_loss != 0 else 0
                
                # Update atau create performance record
                performance_stmt = (
                    select(SignalPerformance)
                    .where(SignalPerformance.strategy_name == strategy_name)
                )
                
                result = await session.execute(performance_stmt)
                performance = result.scalar_one_or_none()
                
                if not performance:
                    performance = SignalPerformance(
                        strategy_name=strategy_name,
                        symbol="ALL",
                        period_start=datetime.now() - timedelta(days=30)
                    )
                    session.add(performance)
                    
                # Update metrics
                performance.total_signals = total_signals
                performance.winning_signals = winning_signals
                performance.losing_signals = losing_signals
                performance.win_rate = win_rate
                performance.avg_profit = avg_profit
                performance.avg_loss = avg_loss
                performance.profit_factor = profit_factor
                performance.period_end = datetime.now()

                await self._learn(session, strategy_name, winning_signals + losing_signals,
                                  win_rate, float(avg_profit), float(avg_loss))
                await session.commit()
                
        except Exception as e:
            logger.error(f"❌ Error calculating strategy performance for {strategy_name}: {e}")
            
    async def _learn(self, session, strategy_name: str, closed: int, win_rate: float,
                     avg_profit: float, avg_loss: float):
        """Sesuaikan ambang & status strategi berdasarkan hasilnya sendiri (lihat signals/learning.py)."""
        from sqlalchemy import select
        cfg = (await session.execute(
            select(StrategyConfig).where(StrategyConfig.strategy_name == strategy_name)
        )).scalar_one_or_none()
        if not cfg:  # strategi baru (mis. Fundamental/Sentiment) ikut dikelola Brain
            cfg = StrategyConfig(strategy_name=strategy_name, enabled=True,
                                 min_confidence=self.parameters.min_confidence, max_positions=5,
                                 risk_per_trade=0.02, trading_hours_only=False, min_time_between_signals=3600)
            session.add(cfg)
            await session.flush()
        a = adapt(float(cfg.min_confidence), cfg.enabled, closed, win_rate, avg_profit, avg_loss)
        changed = a.min_confidence != float(cfg.min_confidence) or a.enabled != cfg.enabled
        cfg.min_confidence, cfg.enabled = a.min_confidence, a.enabled
        await session.flush()
        await session.refresh(cfg)  # hindari lazy-load kolom server-default di konteks async
        self.strategy_configs[strategy_name] = cfg.to_dict()
        if changed:
            event = {
                "time": datetime.now().isoformat(), "strategy": strategy_name, "reason": a.reason,
                "expectancy": round(a.expectancy, 3), "win_rate": round(win_rate, 1), "closed": closed,
                "min_confidence": a.min_confidence, "enabled": a.enabled,
            }
            self.brain_log.appendleft(event)
            logger.info(f"🧠 {strategy_name}: {a.reason}")
            await self.websocket_manager.broadcast({'type': 'brain_update', 'data': event}, channel='signals')

    async def get_signals(self, symbol: str = None) -> List[dict]:
        """Get signals untuk symbol atau semua symbols"""
        try:
            if symbol:
                # Return signals untuk specific symbol
                if symbol in self.active_signals:
                    return [signal.to_dict() for signal in self.active_signals[symbol]]
                return []
            else:
                # Return semua active signals
                all_signals = []
                for signals in self.active_signals.values():
                    all_signals.extend([signal.to_dict() for signal in signals])
                return all_signals
                
        except Exception as e:
            logger.error(f"❌ Error getting signals: {e}")
            return []