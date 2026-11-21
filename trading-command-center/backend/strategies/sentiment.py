"""
Sentiment Analysis Strategy untuk Trading Command Center
Analisis sentimen dari news dan social media
"""

import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models.signals import TradingSignal, SignalType, TimeFrame
from .base import BaseStrategy
from news_sentiment.analyzer import SentimentAnalyzer
from utils.logger import setup_logging

logger = setup_logging()


class SentimentStrategy(BaseStrategy):
    """Strategi sentiment analysis dari news dan market data"""
    
    def __init__(self):
        super().__init__("SentimentAnalysis")
        self.sentiment_analyzer = SentimentAnalyzer()
        self.sentiment_cache: Dict[str, Dict] = {}
        self.cache_ttl = 3600  # 1 hour
        
    async def generate_signals(self, symbol: str, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals berdasarkan sentiment analysis"""
        signals = []
        
        try:
            # Get sentiment score
            sentiment_score = await self._get_sentiment_score(symbol)
            
            if sentiment_score is None:
                return signals
                
            # Analyze price action vs sentiment
            price_sentiment_divergence = await self._analyze_price_sentiment_divergence(
                symbol, market_data, sentiment_score
            )
            
            # Generate signal jika ada divergence atau sentiment ekstrem
            if abs(sentiment_score) > 0.6 or abs(price_sentiment_divergence) > 0.4:
                signal = await self._create_sentiment_signal(
                    symbol, sentiment_score, price_sentiment_divergence, market_data
                )
                if signal:
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error generating sentiment signals for {symbol}: {e}")
            
        return signals
        
    async def _get_sentiment_score(self, symbol: str) -> Optional[float]:
        """Get sentiment score untuk symbol"""
        try:
            # Check cache
            cache_key = f"sentiment_{symbol}"
            current_time = datetime.now()
            
            if cache_key in self.sentiment_cache:
                cached_data = self.sentiment_cache[cache_key]
                if (current_time - cached_data['timestamp']).total_seconds() < self.cache_ttl:
                    return cached_data['score']
                    
            # Get news sentiment
            news_sentiment = await self.sentiment_analyzer.get_news_sentiment(symbol)
            
            # Get social media sentiment (jika tersedia)
            social_sentiment = await self.sentiment_analyzer.get_social_sentiment(symbol)
            
            # Combine sentiments
            combined_score = 0.0
            weight_news = 0.7
            weight_social = 0.3
            
            if news_sentiment is not None:
                combined_score += news_sentiment * weight_news
            if social_sentiment is not None:
                combined_score += social_sentiment * weight_social
                
            # Cache result
            self.sentiment_cache[cache_key] = {
                'score': combined_score,
                'timestamp': current_time,
                'news_sentiment': news_sentiment,
                'social_sentiment': social_sentiment
            }
            
            return combined_score
            
        except Exception as e:
            logger.error(f"❌ Error getting sentiment score for {symbol}: {e}")
            return None
            
    async def _analyze_price_sentiment_divergence(self, symbol: str, market_data: Dict[str, Any], 
                                                sentiment_score: float) -> float:
        """Analyze divergence antara price action dan sentiment"""
        try:
            # Get price change
            change_percent = market_data.get('change_percent', 0)
            
            # Normalize price change ke range -1 sampai 1
            price_sentiment = max(-1, min(1, change_percent / 10))  # 10% = full sentiment
            
            # Calculate divergence
            divergence = sentiment_score - price_sentiment
            
            return divergence
            
        except Exception as e:
            logger.error(f"❌ Error analyzing price-sentiment divergence for {symbol}: {e}")
            return 0.0
            
    async def _create_sentiment_signal(self, symbol: str, sentiment_score: float, 
                                     divergence: float, market_data: Dict[str, Any]) -> Optional[TradingSignal]:
        """Create sentiment-based signal"""
        try:
            current_price = market_data.get('current_price')
            change_percent = market_data.get('change_percent', 0)
            
            # Determine signal type
            if sentiment_score > 0.6 and divergence > 0.3:
                # Sentiment sangat positif, price belum mengikuti
                signal_type = SignalType.BUY
                confidence = min(85, 70 + abs(sentiment_score) * 20)
            elif sentiment_score < -0.6 and divergence < -0.3:
                # Sentiment sangat negatif, price belum mengikuti
                signal_type = SignalType.SELL
                confidence = min(85, 70 + abs(sentiment_score) * 20)
            elif abs(sentiment_score) > 0.7:
                # Sentiment ekstrem
                signal_type = SignalType.BUY if sentiment_score > 0 else SignalType.SELL
                confidence = min(80, 60 + abs(sentiment_score) * 25)
            else:
                return None
                
            # Calculate levels
            entry_price = current_price
            
            if signal_type == SignalType.BUY:
                stop_loss = current_price * 0.97  # 3% stop loss
                target_price_1 = current_price * 1.08  # 8% target
                target_price_2 = current_price * 1.15  # 15% target
            else:
                stop_loss = current_price * 1.03  # 3% stop loss
                target_price_1 = current_price * 0.92  # 8% target
                target_price_2 = current_price * 0.85  # 15% target
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Create analysis text
            analysis_text = self._format_sentiment_analysis(
                sentiment_score, divergence, change_percent
            )
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="Sentiment_Analysis",
                timeframe=TimeFrame.D1,
                confidence_score=confidence,
                entry_price=entry_price,
                target_price_1=target_price_1,
                target_price_2=target_price_2,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                sentiment_analysis=analysis_text,
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=12)
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating sentiment signal for {symbol}: {e}")
            return None
            
    def _format_sentiment_analysis(self, sentiment_score: float, divergence: float, price_change: float) -> str:
        """Format sentiment analysis text"""
        sentiment_text = "Very Positive" if sentiment_score > 0.6 else "Positive" if sentiment_score > 0.2 else "Neutral" if abs(sentiment_score) < 0.2 else "Negative" if sentiment_score < -0.2 else "Very Negative"
        
        analysis = f"Sentiment Analysis Score: {sentiment_score:.2f} ({sentiment_text})\n"
        analysis += f"Price-Sentiment Divergence: {divergence:.2f}\n"
        analysis += f"Price Change: {price_change:.2f}%\n"
        
        if abs(divergence) > 0.3:
            analysis += f"{'Positive' if divergence > 0 else 'Negative'} sentiment divergence detected\n"
            
        analysis += f"Signal Type: {'Contrarian' if abs(divergence) > 0.3 else 'Momentum'}"
        
        return analysis