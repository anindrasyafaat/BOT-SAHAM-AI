"""
Machine Learning Ensemble Strategy untuk Trading Command Center.

Model nyata (bukan simulasi): RandomForest + XGBoost + LogisticRegression dilatih pada candle harian
semua simbol, target = harga naik dalam HORIZON hari ke depan. Dilatih ulang tiap hari dan diuji
out-of-sample pada periode terakhir; sinyal hanya keluar bila akurasi uji di atas MIN_TEST_ACCURACY.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from models.signals import SignalType, TimeFrame, TradingSignal
from utils.logger import setup_logging

from .base import BaseStrategy

logger = setup_logging()

HORIZON = 5               # hari ke depan yang diprediksi
TEST_FRACTION = 0.2       # 20% tanggal terakhir untuk uji out-of-sample
MIN_TEST_ACCURACY = 0.52  # di bawah ini model dianggap tak lebih baik dari tebakan
MIN_PROBABILITY = 0.60    # ambang probabilitas untuk mengeluarkan sinyal
RETRAIN_EVERY = timedelta(hours=24)
FEATURES = [
    "ret_1", "ret_5", "ret_10", "ma_5_20", "ma_10_50", "vol_5", "vol_20",
    "volume_ratio", "rsi", "bb_position", "macd_hist_norm", "stoch_k",
]


def feature_frame(df: pd.DataFrame) -> pd.DataFrame:
    """Fitur tak berskala harga (rasio/persen) agar bisa dipakai lintas simbol."""
    c, h, l, v = df["close_price"], df["high_price"], df["low_price"], df["volume"]
    f = pd.DataFrame(index=df.index)
    f["ret_1"], f["ret_5"], f["ret_10"] = c.pct_change(), c.pct_change(5), c.pct_change(10)
    f["ma_5_20"] = c.rolling(5).mean() / c.rolling(20).mean() - 1
    f["ma_10_50"] = c.rolling(10).mean() / c.rolling(50).mean() - 1
    f["vol_5"], f["vol_20"] = f["ret_1"].rolling(5).std(), f["ret_1"].rolling(20).std()
    f["volume_ratio"] = v / v.rolling(20).mean()
    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    f["rsi"] = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    mid, sd = c.rolling(20).mean(), c.rolling(20).std()
    f["bb_position"] = (c - (mid - 2 * sd)) / (4 * sd)
    macd = c.ewm(span=12).mean() - c.ewm(span=26).mean()
    f["macd_hist_norm"] = (macd - macd.ewm(span=9).mean()) / c
    f["stoch_k"] = (c - l.rolling(14).min()) / (h.rolling(14).max() - l.rolling(14).min())
    return f.replace([np.inf, -np.inf], np.nan)


def to_strategy_frame(raw: pd.DataFrame) -> pd.DataFrame:
    return raw.rename(columns={"Open": "open_price", "High": "high_price", "Low": "low_price",
                               "Close": "close_price", "Volume": "volume"})


class MLEnsembleStrategy(BaseStrategy):
    def __init__(self):
        super().__init__("ML_Ensemble")
        self.models: Dict[str, Any] = {}
        self.trained_at: Optional[datetime] = None
        self.test_accuracy: Optional[float] = None
        self.train_rows = 0

    def _build_models(self):
        return {
            "random_forest": RandomForestClassifier(n_estimators=200, max_depth=6, min_samples_leaf=50,
                                                    n_jobs=-1, random_state=42),
            "xgboost": xgb.XGBClassifier(n_estimators=200, max_depth=3, learning_rate=0.05, subsample=0.8,
                                         colsample_bytree=0.8, random_state=42, n_jobs=2, verbosity=0),
            "logistic": make_pipeline(StandardScaler(), LogisticRegression(max_iter=500)),
        }

    def needs_training(self) -> bool:
        return self.trained_at is None or datetime.now() - self.trained_at > RETRAIN_EVERY

    def train(self, histories: Dict[str, pd.DataFrame]) -> Optional[float]:
        """Latih ensemble pada semua simbol (sinkron; panggil lewat asyncio.to_thread)."""
        self.trained_at = datetime.now()  # waktu percobaan: gagal pun menunggu RETRAIN_EVERY
        parts = []
        for sym, raw in histories.items():
            df = to_strategy_frame(raw)
            f = feature_frame(df)
            f["y"] = (df["close_price"].shift(-HORIZON) / df["close_price"] - 1 > 0).astype(float)
            f.loc[f.index[-HORIZON:], "y"] = np.nan  # label masa depan belum diketahui
            f["date"] = [d.date() for d in f.index]
            parts.append(f.dropna())
        if not parts:
            return None
        data = pd.concat(parts)
        if len(data) < 1000:
            logger.warning(f"⚠️ ML: data latih terlalu sedikit ({len(data)} baris)")
            return None
        dates = sorted(data["date"].unique())
        cutoff = dates[int(len(dates) * (1 - TEST_FRACTION))]
        # jeda HORIZON hari agar label train tidak bocor ke periode uji
        gap = dates[max(0, dates.index(cutoff) - HORIZON)]
        train, test = data[data["date"] < gap], data[data["date"] >= cutoff]
        models = self._build_models()
        for m in models.values():
            m.fit(train[FEATURES], train["y"])
        prob = np.mean([m.predict_proba(test[FEATURES])[:, 1] for m in models.values()], axis=0)
        acc = float(((prob >= 0.5) == test["y"].astype(bool)).mean())
        for m in models.values():  # model akhir memakai seluruh data
            m.fit(data[FEATURES], data["y"])
        self.models, self.test_accuracy, self.train_rows = models, acc, len(data)
        logger.info(f"🤖 ML ensemble dilatih: {len(data)} baris, akurasi uji out-of-sample {acc:.1%}")
        return acc

    def predict_proba(self, df: pd.DataFrame) -> Optional[float]:
        if not self.models:
            return None
        row = feature_frame(df)[FEATURES].iloc[[-1]]
        if row.isna().any(axis=None):
            return None
        return float(np.mean([m.predict_proba(row)[:, 1][0] for m in self.models.values()]))

    async def generate_signals(self, symbol: str, df: pd.DataFrame, market_data: Dict[str, Any]) -> List[TradingSignal]:
        if not self.models or (self.test_accuracy or 0) < MIN_TEST_ACCURACY or not self.validate_data(df, min_bars=60):
            return []
        try:
            p = self.predict_proba(df)
            if p is None or (1 - MIN_PROBABILITY) < p < MIN_PROBABILITY:
                return []
            prediction = 1 if p >= MIN_PROBABILITY else 0
            confidence = p if prediction else 1 - p
            signal = await self._create_ml_signal(symbol, prediction, p, confidence, market_data, df)
            return [signal] if signal else []
        except Exception as e:
            logger.error(f"❌ Error generating ML ensemble signals for {symbol}: {e}")
            return []

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
                timeframe=TimeFrame.D1,
                confidence_score=confidence * 100,  # Convert to percentage
                entry_price=entry_price,
                target_price_1=target_price_1,
                stop_loss=stop_loss,
                risk_reward_ratio=risk_reward,
                technical_analysis=f"ML Ensemble: peluang naik {HORIZON} hari {probability:.1%} "
                                 f"(confidence {confidence:.1%}). "
                                 f"{features_summary}",
                generated_at=datetime.now(),
                expires_at=datetime.now() + timedelta(hours=24)
            )
            
        except Exception as e:
            logger.error(f"❌ Error creating ML signal for {symbol}: {e}")
            return None
            
    async def _get_features_summary(self, df: pd.DataFrame) -> str:
        f = feature_frame(df).iloc[-1]
        return (f"RSI {f['rsi']:.1f}, posisi BB {f['bb_position']:.2f}, volume {f['volume_ratio']:.2f}x; "
                f"akurasi uji model {self.test_accuracy:.1%}, horizon {HORIZON} hari")
