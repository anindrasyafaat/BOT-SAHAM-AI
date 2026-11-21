"""
Konteks pasar berbucket. Bucket inilah "bahasa pengalaman": sinyal, analog historis, dan pola semuanya
dibandingkan lewat bucket yang sama, sehingga pengalaman lama bisa dipakai untuk kondisi sekarang.
"""

from typing import Optional

import numpy as np
import pandas as pd

CANDLE_KEYS = ("regime", "rsi", "volatilitas", "volume")  # bisa dihitung dari candle (dipakai analog)


def feature_frame(raw: pd.DataFrame) -> pd.DataFrame:
    """Bucket per hari dari candle Yahoo (kolom Open/High/Low/Close/Volume)."""
    c, v = raw["Close"].astype(float), raw["Volume"].astype(float)
    ma50, ma200 = c.rolling(50).mean(), c.rolling(200).mean()
    regime = np.select([(c > ma50) & (ma50 > ma200), (c < ma50) & (ma50 < ma200)], ["naik", "turun"], "sideways")
    regime = pd.Series(regime, index=raw.index).where(ma200.notna())

    delta = c.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / 14, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / 14, adjust=False).mean()
    rsi = 100 - 100 / (1 + gain / loss.replace(0, np.nan))
    rsi = rsi.where(loss != 0, 100.0)
    rsi_b = pd.cut(rsi, [-np.inf, 30, 50, 70, np.inf], labels=["oversold", "lemah", "kuat", "overbought"]).astype(object)

    r = c.pct_change()
    ratio = r.rolling(20).std() / r.rolling(252, min_periods=120).std()
    vol_b = pd.cut(ratio, [-np.inf, 0.8, 1.25, np.inf], labels=["rendah", "normal", "tinggi"]).astype(object)

    vr = v / v.rolling(20).mean()
    volu_b = pd.cut(vr, [-np.inf, 0.7, 1.5, np.inf], labels=["rendah", "normal", "tinggi"]).astype(object)

    out = pd.DataFrame({"regime": regime, "rsi": rsi_b, "volatilitas": vol_b, "volume": volu_b,
                        "rsi_value": rsi, "close": c}, index=raw.index)
    return out.replace({np.nan: None})


def market_of(symbol: str) -> str:
    return "IDX" if symbol.endswith(".JK") else "kripto" if symbol.endswith("USDT") else "US"


def bucket_fear_greed(value: Optional[float]) -> Optional[str]:
    if value is None:
        return None
    return "takut" if value < 45 else "serakah" if value > 55 else "netral"


def bucket_sentiment(score: Optional[float]) -> Optional[str]:
    if score is None:
        return None
    return "negatif" if score < -0.1 else "positif" if score > 0.1 else "netral"


def context_at(symbol: str, raw: Optional[pd.DataFrame], when=None, fear_greed: Optional[float] = None,
               news_sentiment: Optional[float] = None) -> dict:
    """Konteks sebuah simbol pada tanggal `when` (default: candle terakhir)."""
    ctx = {"pasar": market_of(symbol), "fear_greed": bucket_fear_greed(fear_greed),
           "sentimen": bucket_sentiment(news_sentiment)}
    if raw is None or len(raw) < 2:
        return ctx
    f = feature_frame(raw)
    if when is not None:
        idx = [d.date() for d in f.index]
        day = when.date() if hasattr(when, "date") else when
        pos = max((i for i, d in enumerate(idx) if d <= day), default=None)
        if pos is None:
            return ctx
        row = f.iloc[pos]
    else:
        row = f.iloc[-1]
    ctx.update({k: row[k] for k in CANDLE_KEYS})
    ctx["rsi_value"] = round(float(row["rsi_value"]), 1) if row["rsi_value"] is not None else None
    return ctx
