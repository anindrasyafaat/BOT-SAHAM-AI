"""
Fundamental Analysis Strategy untuk Trading Command Center
Analisis fundamental otomatis untuk stock selection
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from models.signals import TradingSignal, SignalType, TimeFrame
from .base import BaseStrategy
from utils.logger import setup_logging

logger = setup_logging()


class FundamentalStrategy(BaseStrategy):
    """Strategi fundamental analysis untuk stock selection"""
    
    def __init__(self):
        super().__init__("FundamentalAnalysis")
        
    async def generate_signals(self, symbol: str, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals berdasarkan fundamental analysis"""
        signals = []
        
        try:
            # Extract fundamental metrics
            pe_ratio = market_data.get('pe_ratio')
            pb_ratio = market_data.get('pb_ratio')
            dividend_yield = market_data.get('dividend_yield')
            market_cap = market_data.get('market_cap')
            current_price = market_data.get('current_price')
            
            if not all([pe_ratio, pb_ratio, current_price]):
                return signals
                
            # Fundamental scoring
            fundamental_score = await self._calculate_fundamental_score(
                pe_ratio, pb_ratio, dividend_yield, market_cap
            )
            
            # Generate signal jika fundamental kuat
            if fundamental_score >= 70:
                signal = await self._create_fundamental_signal(
                    symbol, fundamental_score, market_data
                )
                if signal:
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error generating fundamental signals for {symbol}: {e}")
            
        return signals
        
    async def _calculate_fundamental_score(self, pe_ratio: float, pb_ratio: float, 
                                         dividend_yield: Optional[float], market_cap: Optional[float]) -> float:
        """Calculate fundamental score berdasarkan metrics"""
        score = 50.0  # Base score
        
        try:
            # PE Ratio Analysis (15-25 considered good)
            if 15 <= pe_ratio <= 25:
                score += 20.0
            elif 10 <= pe_ratio < 15:
                score += 15.0
            elif 25 < pe_ratio <= 35:
                score += 10.0
            else:
                score -= 10.0
                
            # PB Ratio Analysis (1-3 considered good)
            if 1 <= pb_ratio <= 3:
                score += 15.0
            elif 0.5 <= pb_ratio < 1:
                score += 10.0
            elif 3 < pb_ratio <= 5:
                score += 5.0
            else:
                score -= 5.0
                
            # Dividend Yield Analysis
            if dividend_yield:
                if dividend_yield > 0.04:  # >4%
                    score += 15.0
                elif dividend_yield > 0.02:  # >2%
                    score += 10.0
                elif dividend_yield > 0.01:  # >1%
                    score += 5.0
                    
            # Market Cap Analysis
            if market_cap:
                if market_cap > 1e9:  # Large cap
                    score += 5.0
                elif market_cap > 1e8:  # Mid cap
                    score += 3.0
                    
            # Clamp score
            return max(0, min(100, score))
            
        except Exception as e:
            logger.error(f"❌ Error calculating fundamental score: {e}")
            return 50.0
            
    async def _create_fundamental_signal(self, symbol: str, fundamental_score: float, 
                                       market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Create fundamental signal"""
        try:
            current_price = market_data.get('current_price')
            pe_ratio = market_data.get('pe_ratio')
            pb_ratio = market_data.get('pb_ratio')
            dividend_yield = market_data.get('dividend_yield')
            
            # Calculate levels (simplified)
            entry_price = current_price
            stop_loss = current_price * 0.95  # 5% stop loss
            target_price_1 = current_price * 1.10  # 10% target
            target_price_2 = current_price * 1.20  # 20% target
            
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Adjust confidence based on score
            confidence = min(85.0, fundamental_score)
            
            analysis_text = self._format_fundamental_analysis(
                pe_ratio, pb_ratio, dividend_yield, fundamental_score
            )
            
            return TradingSignal(
                symbol=symbol,
                signal_type=SignalType.BUY,
                strategy_name="Fundamental_Analysis",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                target_price_2=target_price_2,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                fundamental_analysis=analysis_text,
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(days=7)
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating fundamental signal for {symbol}: {e}")
            return None
            
    def _format_fundamental_analysis(self, pe_ratio: float, pb_ratio: float, 
                                   dividend_yield: Optional[float], score: float) -> str:
        """Format fundamental analysis text"""
        analysis = f"Fundamental Analysis Score: {score:.1f}/100\n"
        analysis += f"PE Ratio: {pe_ratio:.2f} - {'Good' if 15 <= pe_ratio <= 25 else 'Needs attention'}\n"
        analysis += f"PB Ratio: {pb_ratio:.2f} - {'Good' if 1 <= pb_ratio <= 3 else 'Needs attention'}\n"
        
        if dividend_yield:
            analysis += f"Dividend Yield: {dividend_yield*100:.2f}%\n"
            
        analysis += f"Overall Assessment: {'Strong fundamentals' if score >= 70 else 'Moderate fundamentals' if score >= 50 else 'Weak fundamentals'}"
        
        return analysis