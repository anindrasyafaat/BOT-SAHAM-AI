"""
Technical Analysis Strategies untuk Trading Command Center
Implementasi 8 strategi technical analysis otomatis
"""

import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from models.signals import TradingSignal, SignalType, TimeFrame
from .base import BaseStrategy
import pandas_ta as ta
from utils.logger import setup_logging

logger = setup_logging()


class TechnicalStrategy(BaseStrategy):
    """Strategi technical analysis dengan multiple indicators"""
    
    def __init__(self):
        super().__init__("TechnicalAnalysis")
        
    async def generate_signals(self, symbol: str, df: pd.DataFrame, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals menggunakan multiple technical strategies"""
        signals = []
        
        try:
            if df.empty or len(df) < 50:  # Minimum data requirement
                return signals
                
            current_price = market_data.get('current_price', df['close_price'].iloc[-1])
            
            # Strategy 1: EMA Crossover dengan Volume Profile
            ema_signal = await self._ema_crossover_strategy(symbol, df, current_price)
            if ema_signal:
                signals.append(ema_signal)
                
            # Strategy 2: SuperTrend dengan RSI Divergence
            supertrend_signal = await self._supertrend_rsi_strategy(symbol, df, current_price)
            if supertrend_signal:
                signals.append(supertrend_signal)
                
            # Strategy 3: Bollinger Bands Squeeze dengan MACD
            bb_macd_signal = await self._bollinger_macd_strategy(symbol, df, current_price)
            if bb_macd_signal:
                signals.append(bb_macd_signal)
                
            # Strategy 4: VWAP dengan Order Block (ICT Concept)
            vwap_signal = await self._vwap_orderblock_strategy(symbol, df, current_price)
            if vwap_signal:
                signals.append(vwap_signal)
                
            # Strategy 5: Breakout 52-week high dengan Volume Surge
            breakout_signal = await self._breakout_volume_strategy(symbol, df, current_price, market_data)
            if breakout_signal:
                signals.append(breakout_signal)
                
            # Strategy 6: Mean Reversion dengan Z-score
            mean_reversion_signal = await self._mean_reversion_strategy(symbol, df, current_price)
            if mean_reversion_signal:
                signals.append(mean_reversion_signal)
                
            # Strategy 7: Liquidity Sweep Detector
            liquidity_signal = await self._liquidity_sweep_strategy(symbol, df, current_price)
            if liquidity_signal:
                signals.append(liquidity_signal)
                
            # Strategy 8: Golden Cross / Death Cross
            golden_cross_signal = await self._golden_cross_strategy(symbol, df, current_price)
            if golden_cross_signal:
                signals.append(golden_cross_signal)
                
            # Strategy 9: Heikin-Ashi Trend Following
            ha_signal = await self._heikin_ashi_strategy(symbol, df, current_price)
            if ha_signal:
                signals.append(ha_signal)
                
        except Exception as e:
            logger.error(f"❌ Error generating technical signals for {symbol}: {e}")
            
        return signals
        
    async def _ema_crossover_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """EMA 8/21 Crossover dengan Volume Profile"""
        try:
            # Calculate EMAs
            df['EMA_8'] = ta.ema(df['close_price'], length=8)
            df['EMA_21'] = ta.ema(df['close_price'], length=21)
            
            # Get latest values
            ema_8_current = df['EMA_8'].iloc[-1]
            ema_21_current = df['EMA_21'].iloc[-1]
            ema_8_prev = df['EMA_8'].iloc[-2]
            ema_21_prev = df['EMA_21'].iloc[-2]
            
            # Check crossover
            bullish_crossover = (ema_8_prev <= ema_21_prev) and (ema_8_current > ema_21_current)
            bearish_crossover = (ema_8_prev >= ema_21_prev) and (ema_8_current < ema_21_current)
            
            if not (bullish_crossover or bearish_crossover):
                return None
                
            # Volume confirmation
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_confirmed = current_volume > avg_volume * 1.5
            
            if not volume_confirmed:
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if bullish_crossover else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            stop_loss = min(df['low_price'].iloc[-5:]) if bullish_crossover else max(df['high_price'].iloc[-5:])
            target_price_1 = entry_price + (entry_price - stop_loss) * 1.5 if bullish_crossover else entry_price - (stop_loss - entry_price) * 1.5
            target_price_2 = entry_price + (entry_price - stop_loss) * 2.0 if bullish_crossover else entry_price - (stop_loss - entry_price) * 2.0
            
            # Risk/Reward ratio
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence score
            confidence = 75.0
            if volume_confirmed:
                confidence += 10.0
            if risk_reward > 1.5:
                confidence += 5.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="EMA_Crossover",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                target_price_2=target_price_2,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"EMA 8/21 {'bullish' if bullish_crossover else 'bearish'} crossover with volume confirmation. Current volume: {current_volume:.0f}, Average: {avg_volume:.0f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ EMA Crossover strategy error for {symbol}: {e}")
            return None
            
    async def _supertrend_rsi_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """SuperTrend ATR dengan RSI Divergence"""
        try:
            # Calculate SuperTrend
            supertrend = ta.supertrend(df['high_price'], df['low_price'], df['close_price'], length=10, multiplier=3.0)
            df['Supertrend'] = supertrend['SUPERT_10_3.0']
            df['Supertrend_Direction'] = supertrend['SUPERTd_10_3.0']
            
            # Calculate RSI
            df['RSI'] = ta.rsi(df['close_price'], length=14)
            
            # Get latest values
            supertrend_current = df['Supertrend'].iloc[-1]
            supertrend_direction = df['Supertrend_Direction'].iloc[-1]
            supertrend_prev_direction = df['Supertrend_Direction'].iloc[-2]
            rsi_current = df['RSI'].iloc[-1]
            
            # Check signals
            bullish_signal = (supertrend_prev_direction <= 0) and (supertrend_direction > 0) and (rsi_current > 50)
            bearish_signal = (supertrend_prev_direction >= 0) and (supertrend_direction < 0) and (rsi_current < 50)
            
            if not (bullish_signal or bearish_signal):
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if bullish_signal else SignalType.SELL
            
            # Calculate levels
            atr = ta.atr(df['high_price'], df['low_price'], df['close_price'], length=14).iloc[-1]
            entry_price = current_price
            
            if bullish_signal:
                stop_loss = entry_price - atr * 2
                target_price_1 = entry_price + atr * 3
            else:
                stop_loss = entry_price + atr * 2
                target_price_1 = entry_price - atr * 3
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 78.0
            if 30 < rsi_current < 70:  # RSI not in extreme zones
                confidence += 7.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="SuperTrend_RSI",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"SuperTrend {'bullish' if bullish_signal else 'bearish'} flip with RSI confirmation. RSI: {rsi_current:.1f}, ATR: {atr:.2f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ SuperTrend RSI strategy error for {symbol}: {e}")
            return None
            
    async def _bollinger_macd_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Bollinger Bands Squeeze dengan MACD"""
        try:
            # Calculate Bollinger Bands
            bb = ta.bbands(df['close_price'], length=20, std=2)
            # urutan kolom bbands stabil (L, M, U) di pandas-ta 0.3 & 0.4, namanya tidak
            df['BB_Upper'] = bb.iloc[:, 2]
            df['BB_Lower'] = bb.iloc[:, 0]
            df['BB_Middle'] = bb.iloc[:, 1]
            df['BB_Width'] = df['BB_Upper'] - df['BB_Lower']
            
            # Calculate MACD
            macd = ta.macd(df['close_price'], fast=12, slow=26, signal=9)
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_Signal'] = macd['MACDs_12_26_9']
            df['MACD_Histogram'] = macd['MACDh_12_26_9']
            
            # Check Bollinger Squeeze
            bb_width_current = df['BB_Width'].iloc[-1]
            bb_width_avg = df['BB_Width'].rolling(20).mean().iloc[-1]
            squeeze_condition = bb_width_current < bb_width_avg * 0.8
            
            # Check MACD crossover
            macd_current = df['MACD'].iloc[-1]
            macd_signal_current = df['MACD_Signal'].iloc[-1]
            macd_prev = df['MACD'].iloc[-2]
            macd_signal_prev = df['MACD_Signal'].iloc[-2]
            
            macd_bullish = (macd_prev <= macd_signal_prev) and (macd_current > macd_signal_current)
            macd_bearish = (macd_prev >= macd_signal_prev) and (macd_current < macd_signal_current)
            
            if not squeeze_condition or not (macd_bullish or macd_bearish):
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if macd_bullish else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            bb_upper = df['BB_Upper'].iloc[-1]
            bb_lower = df['BB_Lower'].iloc[-1]
            
            if macd_bullish:
                stop_loss = bb_lower
                target_price_1 = bb_upper
            else:
                stop_loss = bb_upper
                target_price_1 = bb_lower
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 72.0
            if squeeze_condition:
                confidence += 8.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Bollinger_MACD",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"Bollinger Squeeze breakout with MACD confirmation. BB Width: {bb_width_current:.2f}, MACD: {macd_current:.3f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Bollinger MACD strategy error for {symbol}: {e}")
            return None
            
    async def _vwap_orderblock_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """VWAP dengan Order Block (ICT Concept)"""
        try:
            # Calculate VWAP
            # VWAP bergulir 20 candle: ta.vwap berjangkar harian sehingga tak bermakna di candle harian
            tp = (df['high_price'] + df['low_price'] + df['close_price']) / 3
            df['VWAP'] = (tp * df['volume']).rolling(20).sum() / df['volume'].rolling(20).sum()
            
            # Calculate order blocks (simplified)
            df['OrderBlock_High'] = df['high_price'].rolling(5).max()
            df['OrderBlock_Low'] = df['low_price'].rolling(5).min()
            
            # Get latest values
            vwap_current = df['VWAP'].iloc[-1]
            ob_high = df['OrderBlock_High'].iloc[-1]
            ob_low = df['OrderBlock_Low'].iloc[-1]
            
            # Check conditions
            bullish_condition = (current_price > vwap_current) and (current_price <= ob_low * 1.02)
            bearish_condition = (current_price < vwap_current) and (current_price >= ob_high * 0.98)
            
            if not (bullish_condition or bearish_condition):
                return None
                
            # Volume confirmation
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_confirmed = current_volume > avg_volume
            
            if not volume_confirmed:
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if bullish_condition else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            
            # target 2R dari risiko ke stop (rumus lama berbasis VWAP bisa menaruh target di sisi yang salah)
            if bullish_condition:
                stop_loss = ob_low * 0.99
                target_price_1 = current_price + 2 * (current_price - stop_loss)
            else:
                stop_loss = ob_high * 1.01
                target_price_1 = current_price - 2 * (stop_loss - current_price)
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 78.0
            if volume_confirmed:
                confidence += 7.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="VWAP_OrderBlock",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"VWAP Order Block {'bullish' if bullish_condition else 'bearish'} setup. VWAP: {vwap_current:.2f}, OB Range: {ob_low:.2f}-{ob_high:.2f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ VWAP OrderBlock strategy error for {symbol}: {e}")
            return None
            
    async def _breakout_volume_strategy(self, symbol: str, df: pd.DataFrame, current_price: float, market_data: Dict) -> Optional[TradingSignal]:
        """Breakout 52-week high dengan Volume Surge"""
        try:
            # Get 52-week high
            fifty_two_week_high = market_data.get('fifty_two_week_high')
            if not fifty_two_week_high:
                return None
                
            # Check breakout condition
            breakout_threshold = fifty_two_week_high * 0.98
            breakout_condition = current_price >= breakout_threshold
            
            if not breakout_condition:
                return None
                
            # Volume surge confirmation
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_surge = current_volume > avg_volume * 2.0
            
            if not volume_surge:
                return None
                
            # Generate signal
            signal_type = SignalType.STRONG_BUY
            
            # Calculate levels
            entry_price = current_price
            stop_loss = fifty_two_week_high * 0.95
            target_price_1 = entry_price + (entry_price - stop_loss) * 2
            
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 85.0
            if volume_surge:
                confidence += 10.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Breakout_Volume",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"52-week high breakout with volume surge. 52W High: {fifty_two_week_high:.2f}, Volume: {current_volume:.0f} (vs Avg: {avg_volume:.0f})",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=48)
            )
            
        except Exception as e:
            logger.error(f"❌ Breakout Volume strategy error for {symbol}: {e}")
            return None
            
    async def _mean_reversion_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Mean Reversion dengan Z-score"""
        try:
            # Calculate moving average and standard deviation
            df['MA_20'] = ta.sma(df['close_price'], length=20)
            df['STD_20'] = ta.stdev(df['close_price'], length=20)
            df['Z_Score'] = (df['close_price'] - df['MA_20']) / df['STD_20']
            
            # Get latest values
            z_score_current = df['Z_Score'].iloc[-1]
            z_score_prev = df['Z_Score'].iloc[-2]
            ma_20 = df['MA_20'].iloc[-1]
            
            # Check mean reversion conditions
            oversold_condition = (z_score_prev <= -2.0) and (z_score_current > -2.0)
            overbought_condition = (z_score_prev >= 2.0) and (z_score_current < 2.0)
            
            if not (oversold_condition or overbought_condition):
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if oversold_condition else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            
            if oversold_condition:
                stop_loss = entry_price * 0.98
                target_price_1 = ma_20
            else:
                stop_loss = entry_price * 1.02
                target_price_1 = ma_20
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 68.0
            if abs(z_score_current) > 2.5:
                confidence += 12.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Mean_Reversion",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"Mean reversion from {'oversold' if oversold_condition else 'overbought'} condition. Z-Score: {z_score_current:.2f}, MA20: {ma_20:.2f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Mean Reversion strategy error for {symbol}: {e}")
            return None
            
    async def _liquidity_sweep_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Liquidity Sweep Detector"""
        try:
            # Find recent highs and lows (liquidity zones)
            recent_highs = df['high_price'].rolling(10).max()
            recent_lows = df['low_price'].rolling(10).min()
            
            # Check for sweep patterns
            current_high = df['high_price'].iloc[-1]
            current_low = df['low_price'].iloc[-1]
            prev_high = df['high_price'].iloc[-2]
            prev_low = df['low_price'].iloc[-2]
            
            # Sweep conditions
            bullish_sweep = (prev_low <= recent_lows.iloc[-2] * 1.01) and (current_low > prev_low) and (current_price > df['close_price'].iloc[-2])
            bearish_sweep = (prev_high >= recent_highs.iloc[-2] * 0.99) and (current_high < prev_high) and (current_price < df['close_price'].iloc[-2])
            
            if not (bullish_sweep or bearish_sweep):
                return None
                
            # Volume confirmation
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_spike = current_volume > avg_volume * 3.0
            
            if not volume_spike:
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if bullish_sweep else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            
            if bullish_sweep:
                stop_loss = prev_low * 0.99
                target_price_1 = recent_highs.iloc[-1]
            else:
                stop_loss = prev_high * 1.01
                target_price_1 = recent_lows.iloc[-1]
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 82.0
            if volume_spike:
                confidence += 8.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Liquidity_Sweep",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"{'Bullish' if bullish_sweep else 'Bearish'} liquidity sweep detected. Volume spike: {current_volume:.0f} (vs Avg: {avg_volume:.0f})",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Liquidity Sweep strategy error for {symbol}: {e}")
            return None
            
    async def _golden_cross_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Golden Cross / Death Cross"""
        try:
            # Calculate moving averages
            df['MA_50'] = ta.sma(df['close_price'], length=50)
            df['MA_200'] = ta.sma(df['close_price'], length=200)
            
            # Get latest values
            ma_50_current = df['MA_50'].iloc[-1]
            ma_200_current = df['MA_200'].iloc[-1]
            ma_50_prev = df['MA_50'].iloc[-2]
            ma_200_prev = df['MA_200'].iloc[-2]
            
            # Check crossover
            golden_cross = (ma_50_prev <= ma_200_prev) and (ma_50_current > ma_200_current)
            death_cross = (ma_50_prev >= ma_200_prev) and (ma_50_current < ma_200_current)
            
            if not (golden_cross or death_cross):
                return None
                
            # Volume confirmation
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_confirmed = current_volume > avg_volume
            
            # Generate signal
            signal_type = SignalType.STRONG_BUY if golden_cross else SignalType.STRONG_SELL
            
            # Calculate levels
            entry_price = current_price
            
            if golden_cross:
                stop_loss = min(df['low_price'].iloc[-10:])
                target_price_1 = entry_price + (entry_price - stop_loss) * 2
            else:
                stop_loss = max(df['high_price'].iloc[-10:])
                target_price_1 = entry_price - (stop_loss - entry_price) * 2
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 85.0
            if volume_confirmed:
                confidence += 10.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Golden_Cross",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"{'Golden Cross' if golden_cross else 'Death Cross'} confirmed. MA50: {ma_50_current:.2f}, MA200: {ma_200_current:.2f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=3)
            )
            
        except Exception as e:
            logger.error(f"❌ Golden Cross strategy error for {symbol}: {e}")
            return None
            
    async def _heikin_ashi_strategy(self, symbol: str, df: pd.DataFrame, current_price: float) -> Optional[TradingSignal]:
        """Heikin-Ashi Trend Following"""
        try:
            # Calculate Heikin-Ashi candles
            df['HA_Close'] = (df['open_price'] + df['high_price'] + df['low_price'] + df['close_price']) / 4
            ha_close = df['HA_Close'].to_numpy()
            ha_open_arr = np.empty(len(df))
            ha_open_arr[0] = (df['open_price'].iloc[0] + df['close_price'].iloc[0]) / 2
            for i in range(1, len(df)):
                ha_open_arr[i] = (ha_open_arr[i-1] + ha_close[i-1]) / 2
            df['HA_Open'] = ha_open_arr
                
            df['HA_High'] = df[['high_price', 'HA_Open', 'HA_Close']].max(axis=1)
            df['HA_Low'] = df[['low_price', 'HA_Open', 'HA_Close']].min(axis=1)
            
            # Get latest values
            ha_open = df['HA_Open'].iloc[-1]
            ha_close = df['HA_Close'].iloc[-1]
            ha_high = df['HA_High'].iloc[-1]
            ha_low = df['HA_Low'].iloc[-1]
            
            # Check trend
            bullish_trend = (ha_close > ha_open) and (ha_close > df['HA_Close'].iloc[-2])
            bearish_trend = (ha_close < ha_open) and (ha_close < df['HA_Close'].iloc[-2])
            
            # Volume filter
            current_volume = df['volume'].iloc[-1]
            avg_volume = df['volume'].rolling(20).mean().iloc[-1]
            volume_filter = current_volume > avg_volume
            
            if not (bullish_trend or bearish_trend) or not volume_filter:
                return None
                
            # Generate signal
            signal_type = SignalType.BUY if bullish_trend else SignalType.SELL
            
            # Calculate levels
            entry_price = current_price
            
            if bullish_trend:
                stop_loss = ha_low
                target_price_1 = ha_high + (ha_high - ha_low)
            else:
                stop_loss = ha_high
                target_price_1 = ha_low - (ha_high - ha_low)
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Confidence
            confidence = 73.0
            if volume_filter:
                confidence += 7.0
                
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Heikin_Ashi",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"Heikin-Ashi {'bullish' if bullish_trend else 'bearish'} trend continuation. HA Close: {ha_close:.2f}, HA Open: {ha_open:.2f}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Heikin-Ashi strategy error for {symbol}: {e}")
            return None