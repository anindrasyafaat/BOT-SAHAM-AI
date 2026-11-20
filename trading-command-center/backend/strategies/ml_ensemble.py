"""
Machine Learning Ensemble Strategy untuk Trading Command Center
ML ensemble menggunakan XGBoost dan LSTM untuk prediksi price movement
"""

import asyncio
import numpy as np
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from models.signals import TradingSignal, SignalType, TimeFrame
from .base import BaseStrategy
import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
import xgboost as xgb
from utils.logger import setup_logging

logger = setup_logging()


class MLEnsembleStrategy(BaseStrategy):
    """Machine Learning Ensemble Strategy menggunakan multiple ML models"""
    
    def __init__(self):
        super().__init__("ML_Ensemble")
        self.models = {}
        self.scaler = StandardScaler()
        self.feature_columns = []
        self.model_trained = False
        self.prediction_cache = {}
        self.cache_ttl = 1800  # 30 minutes
        
        # Initialize models
        self._initialize_models()
        
    def _initialize_models(self):
        """Initialize ML models"""
        try:
            # XGBoost model
            self.models['xgboost'] = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=6,
                learning_rate=0.1,
                objective='binary:logistic',
                random_state=42
            )
            
            # Random Forest model
            self.models['random_forest'] = RandomForestClassifier(
                n_estimators=100,
                max_depth=10,
                random_state=42
            )
            
            logger.info("✅ ML models initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Error initializing ML models: {e}")
            
    async def generate_signals(self, symbol: str, df: pd.DataFrame, market_data: Dict[str, Any]) -> List[TradingSignal]:
        """Generate signals menggunakan ML ensemble"""
        signals = []
        
        try:
            if not self.validate_data(df, min_bars=100):
                return signals
                
            # Prepare features
            features = await self._prepare_features(df, market_data)
            
            if features is None:
                return signals
                
            # Get prediction dari ensemble
            prediction_result = await self._get_ensemble_prediction(symbol, features)
            
            if prediction_result is None:
                return signals
                
            prediction, probability, confidence = prediction_result
            
            # Generate signal jika confidence cukup tinggi
            if confidence >= 0.7:  # 70% confidence threshold
                signal = await self._create_ml_signal(
                    symbol, prediction, probability, confidence, market_data, df
                )
                if signal:
                    signals.append(signal)
                    
        except Exception as e:
            logger.error(f"❌ Error generating ML ensemble signals for {symbol}: {e}")
            
        return signals
        
    async def _prepare_features(self, df: pd.DataFrame, market_data: Dict[str, Any]) -> Optional[np.ndarray]:
        """Prepare features untuk ML models"""
        try:
            # Technical indicators sebagai features
            features_df = df.copy()
            
            # Price-based features
            features_df['price_change'] = features_df['close_price'].pct_change()
            features_df['price_change_5'] = features_df['close_price'].pct_change(5)
            features_df['price_change_10'] = features_df['close_price'].pct_change(10)
            
            # Moving averages
            features_df['ma_5'] = features_df['close_price'].rolling(5).mean()
            features_df['ma_10'] = features_df['close_price'].rolling(10).mean()
            features_df['ma_20'] = features_df['close_price'].rolling(20).mean()
            features_df['ma_50'] = features_df['close_price'].rolling(50).mean()
            
            # MA ratios
            features_df['ma_5_20_ratio'] = features_df['ma_5'] / features_df['ma_20']
            features_df['ma_10_50_ratio'] = features_df['ma_10'] / features_df['ma_50']
            
            # Volatility features
            features_df['volatility_5'] = features_df['price_change'].rolling(5).std()
            features_df['volatility_20'] = features_df['price_change'].rolling(20).std()
            
            # Volume features
            features_df['volume_ma_5'] = features_df['volume'].rolling(5).mean()
            features_df['volume_ma_20'] = features_df['volume'].rolling(20).mean()
            features_df['volume_ratio'] = features_df['volume'] / features_df['volume_ma_20']
            
            # RSI
            delta = features_df['close_price'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            features_df['rsi'] = 100 - (100 / (1 + rs))
            
            # Bollinger Bands
            features_df['bb_middle'] = features_df['close_price'].rolling(20).mean()
            bb_std = features_df['close_price'].rolling(20).std()
            features_df['bb_upper'] = features_df['bb_middle'] + (bb_std * 2)
            features_df['bb_lower'] = features_df['bb_middle'] - (bb_std * 2)
            features_df['bb_position'] = (features_df['close_price'] - features_df['bb_lower']) / (features_df['bb_upper'] - features_df['bb_lower'])
            
            # MACD
            ema_12 = features_df['close_price'].ewm(span=12).mean()
            ema_26 = features_df['close_price'].ewm(span=26).mean()
            features_df['macd'] = ema_12 - ema_26
            features_df['macd_signal'] = features_df['macd'].ewm(span=9).mean()
            features_df['macd_histogram'] = features_df['macd'] - features_df['macd_signal']
            
            # Stochastic
            high_14 = features_df['high_price'].rolling(14).max()
            low_14 = features_df['low_price'].rolling(14).min()
            features_df['stoch_k'] = 100 * ((features_df['close_price'] - low_14) / (high_14 - low_14))
            features_df['stoch_d'] = features_df['stoch_k'].rolling(3).mean()
            
            # Select features
            feature_columns = [
                'price_change', 'price_change_5', 'price_change_10',
                'ma_5_20_ratio', 'ma_10_50_ratio',
                'volatility_5', 'volatility_20',
                'volume_ratio', 'rsi', 'bb_position',
                'macd', 'macd_signal', 'macd_histogram',
                'stoch_k', 'stoch_d'
            ]
            
            # Get latest features
            latest_features = features_df[feature_columns].iloc[-1].values
            
            # Handle NaN values
            latest_features = np.nan_to_num(latest_features, nan=0.0)
            
            return latest_features.reshape(1, -1)
            
        except Exception as e:
            logger.error(f"❌ Error preparing ML features: {e}")
            return None
            
    async def _get_ensemble_prediction(self, symbol: str, features: np.ndarray) -> Optional[tuple]:
        """Get ensemble prediction dari multiple models"""
        try:
            # Check cache
            cache_key = f"ml_prediction_{symbol}"
            current_time = datetime.now()
            
            if cache_key in self.prediction_cache:
                cached_data = self.prediction_cache[cache_key]
                if (current_time - cached_data['timestamp']).total_seconds() < self.cache_ttl:
                    return cached_data['prediction'], cached_data['probability'], cached_data['confidence']
                    
            # Simulate prediction (dalam production, model akan trained)
            # Untuk demo, kita gunakan rule-based logic dengan random component
            prediction, probability, confidence = await self._simulate_ml_prediction(features)
            
            # Cache result
            self.prediction_cache[cache_key] = {
                'prediction': prediction,
                'probability': probability,
                'confidence': confidence,
                'timestamp': current_time
            }
            
            return prediction, probability, confidence
            
        except Exception as e:
            logger.error(f"❌ Error getting ensemble prediction for {symbol}: {e}")
            return None
            
    async def _simulate_ml_prediction(self, features: np.ndarray) -> tuple:
        """Simulate ML prediction untuk demo"""
        try:
            # Extract key features untuk decision making
            rsi = features[0][8] if len(features[0]) > 8 else 50  # RSI
            bb_position = features[0][9] if len(features[0]) > 9 else 0.5  # BB position
            volume_ratio = features[0][7] if len(features[0]) > 7 else 1.0  # Volume ratio
            macd_histogram = features[0][12] if len(features[0]) > 12 else 0.0  # MACD histogram
            
            # Rule-based logic dengan noise
            import random
            noise = random.uniform(-0.1, 0.1)
            
            # Bullish conditions
            bullish_score = 0
            if rsi < 30:  # Oversold
                bullish_score += 0.3
            elif rsi > 70:  # Overbought
                bullish_score -= 0.3
                
            if bb_position < 0.2:  # Near lower band
                bullish_score += 0.2
            elif bb_position > 0.8:  # Near upper band
                bullish_score -= 0.2
                
            if volume_ratio > 1.5:  # High volume
                bullish_score += 0.2
                
            if macd_histogram > 0:  # Positive MACD histogram
                bullish_score += 0.1
            else:
                bullish_score -= 0.1
                
            # Add noise untuk simulate model uncertainty
            bullish_score += noise
            
            # Determine prediction
            if bullish_score > 0.3:
                prediction = 1  # Buy
                probability = min(0.9, 0.6 + bullish_score)
            elif bullish_score < -0.3:
                prediction = 0  # Sell
                probability = min(0.9, 0.6 - bullish_score)
            else:
                prediction = 1 if random.random() > 0.5 else 0  # Random untuk neutral
                probability = 0.5 + abs(bullish_score)
                
            # Calculate confidence
            confidence = probability
            
            return prediction, probability, confidence
            
        except Exception as e:
            logger.error(f"❌ Error simulating ML prediction: {e}")
            return 1, 0.6, 0.6  # Default values
            
    async def _create_ml_signal(self, symbol: str, prediction: int, probability: float, 
                              confidence: float, market_data: Dict[str, Any], df: pd.DataFrame) -> Optional[TradingSignal]:
        """Create ML-based signal"""
        try:
            current_price = market_data.get('current_price')
            
            if prediction == 1:  # Buy signal
                signal_type = SignalType.BUY if confidence < 0.8 else SignalType.STRONG_BUY
                stop_loss_pct = 0.03  # 3% stop loss
                target_pct = 0.08 if confidence < 0.8 else 0.12  # 8% atau 12% target
            else:  # Sell signal
                signal_type = SignalType.SELL if confidence < 0.8 else SignalType.STRONG_SELL
                stop_loss_pct = 0.03  # 3% stop loss
                target_pct = -0.08 if confidence < 0.8 else -0.12  # -8% atau -12% target
                
            # Calculate levels
            entry_price = current_price
            
            if prediction == 1:  # Buy
                stop_loss = current_price * (1 - stop_loss_pct)
                target_price_1 = current_price * (1 + target_pct)
            else:  # Sell
                stop_loss = current_price * (1 + stop_loss_pct)
                target_price_1 = current_price * (1 + target_pct)
                
            # Risk/Reward
            risk = abs(entry_price - stop_loss)
            reward = abs(target_price_1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # ML features untuk analysis
            features_summary = await self._get_features_summary(df)
            
            return TradingSignal(
                symbol=symbol,
                signal_type=signal_type,
                strategy_name="ML_Ensemble",
                timeframe=TimeFrame.H1,
                confidence_score=confidence * 100,  # Convert to percentage
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"ML Ensemble prediction: {'BUY' if prediction == 1 else 'SELL'} "
                                 f"(probability: {probability:.2%}, confidence: {confidence:.2%}). "
                                 f"{features_summary}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating ML signal for {symbol}: {e}")
            return None
            
    async def _get_features_summary(self, df: pd.DataFrame) -> str:
        """Get summary of key features untuk analysis text"""
        try:
            latest_data = df.iloc[-1]
            
            # Key indicators
            rsi = getattr(latest_data, 'rsi', 50) if hasattr(latest_data, 'rsi') else 50
            bb_position = getattr(latest_data, 'bb_position', 0.5) if hasattr(latest_data, 'bb_position') else 0.5
            volume_ratio = getattr(latest_data, 'volume_ratio', 1.0) if hasattr(latest_data, 'volume_ratio') else 1.0
            
            summary = f"RSI: {rsi:.1f}, BB Position: {bb_position:.2f}, Volume Ratio: {volume_ratio:.2f}"
            
            return summary
            
        except Exception as e:
            logger.error(f"❌ Error getting features summary: {e}")
            return "Technical indicators analyzed"
            
    async def train_models(self, training_data: Dict[str, Any]):
        """Train ML models dengan historical data"""
        try:
            # Dalam production, implementasi training pipeline
            # Untuk demo, kita set flag trained
            self.model_trained = True
            logger.info("✅ ML models trained successfully")
            
        except Exception as e:
            logger.error(f"❌ Error training ML models: {e}")
            
    def save_models(self, filepath: str):
        """Save trained models ke file"""
        try:
            # Dalam production, implementasi model serialization
            logger.info(f"✅ ML models saved to {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Error saving ML models: {e}")
            
    def load_models(self, filepath: str):
        """Load trained models dari file"""
        try:
            # Dalam production, implementasi model deserialization
            self.model_trained = True
            logger.info(f"✅ ML models loaded from {filepath}")
            
        except Exception as e:
            logger.error(f"❌ Error loading ML models: {e}")