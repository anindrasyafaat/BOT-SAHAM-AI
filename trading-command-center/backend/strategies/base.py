"""
Base Strategy class untuk Trading Command Center
Base class untuk semua trading strategies
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime
from models.signals import TradingSignal
import pandas as pd


class BaseStrategy(ABC):
    """Base class untuk semua trading strategies"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.parameters = {}
        
    @abstractmethod
    async def generate_signals(self, symbol: str, df: pd.DataFrame, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """
        Generate trading signals berdasarkan strategy
        
        Args:
            symbol: Symbol yang akan dianalisis
            df: DataFrame dengan historical data
            market_data: Real-time market data
            
        Returns:
            List of TradingSignal objects
        """
        pass
        
    def validate_data(self, df: pd.DataFrame, min_bars: int = 50) -> bool:
        """
        Validate apakah data cukup untuk analysis
        
        Args:
            df: DataFrame untuk divalidasi
            min_bars: Minimum bars yang dibutuhkan
            
        Returns:
            True jika data valid
        """
        if df.empty:
            return False
            
        if len(df) < min_bars:
            return False
            
        required_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
        for col in required_columns:
            if col not in df.columns:
                return False
                
        return True
        
    def calculate_position_size(self, entry_price: float, stop_loss: float, risk_per_trade: float = 0.02) -> float:
        """
        Calculate position size berdasarkan risk management
        
        Args:
            entry_price: Entry price
            stop_loss: Stop loss price
            risk_per_trade: Risk per trade (default 2%)
            
        Returns:
            Position size
        """
        risk_amount = abs(entry_price - stop_loss)
        if risk_amount == 0:
            return 0
            
        # Position size = (Account Risk) / (Trade Risk)
        # Simplified untuk demo - dalam production gunakan account balance
        return risk_per_trade / (risk_amount / entry_price)
        
    def calculate_risk_reward(self, entry_price: float, target_price: float, stop_loss: float) -> float:
        """
        Calculate risk/reward ratio
        
        Args:
            entry_price: Entry price
            target_price: Target price
            stop_loss: Stop loss price
            
        Returns:
            Risk/reward ratio
        """
        reward = abs(target_price - entry_price)
        risk = abs(entry_price - stop_loss)
        
        if risk == 0:
            return 0
            
        return reward / risk
        
    def is_market_hours(self) -> bool:
        """
        Check apakah dalam market hours
        
        Returns:
            True jika dalam market hours
        """
        from datetime import datetime
        current_hour = datetime.now().hour
        
        # Market hours: 9:00 - 16:00 (EST)
        # Adjust untuk timezone lokal
        return 9 <= current_hour <= 16
        
    def get_confidence_score(self, base_score: float, **factors) -> float:
        """
        Calculate confidence score berdasarkan berbagai factors
        
        Args:
            base_score: Base confidence score
            **factors: Additional factors untuk adjust score
            
        Returns:
            Final confidence score (0-100)
        """
        score = base_score
        
        # Volume confirmation
        if factors.get('volume_confirmed'):
            score += 5.0
            
        # Risk/Reward ratio
        risk_reward = factors.get('risk_reward', 0)
        if risk_reward > 2.0:
            score += 10.0
        elif risk_reward > 1.5:
            score += 5.0
        elif risk_reward < 1.0:
            score -= 10.0
            
        # Market conditions
        if factors.get('trend_aligned'):
            score += 5.0
            
        if factors.get('support_respected'):
            score += 5.0
            
        # Clamp ke range 0-100
        return max(0, min(100, score))
        
    def format_analysis_text(self, strategy_name: str, signal_type: str, **kwargs) -> str:
        """
        Format analysis text untuk signal
        
        Args:
            strategy_name: Nama strategy
            signal_type: Tipe signal (BUY/SELL)
            **kwargs: Additional parameters
            
        Returns:
            Formatted analysis text
        """
        text = f"{strategy_name} generated {signal_type} signal"
        
        # Add key metrics
        for key, value in kwargs.items():
            if value is not None:
                text += f". {key.replace('_', ' ').title()}: {value:.2f}"
                
        return text
        
    def should_generate_signal(self, symbol: str, last_signal_time: Dict[str, datetime], min_interval: int = 300) -> bool:
        """
        Check apakah harus generate signal untuk symbol
        
        Args:
            symbol: Symbol yang akan dicek
            last_signal_time: Dictionary last signal times
            min_interval: Minimum interval antara signals (seconds)
            
        Returns:
            True jika boleh generate signal
        """
        if symbol not in last_signal_time:
            return True
            
        time_since_last = datetime.now() - last_signal_time[symbol]
        return time_since_last.total_seconds() >= min_interval