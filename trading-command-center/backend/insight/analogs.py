"""
Analog historis: "kapan kondisi seperti sekarang pernah terjadi, dan apa yang terjadi sesudahnya?"
Pengalaman instan dari 1 tahun candle semua simbol, tanpa menunggu sinyal tertutup.
"""

from typing import Dict, Optional

import numpy as np
import pandas as pd

from insight.context import CANDLE_KEYS, feature_frame, market_of

KEYS = ("pasar", *CANDLE_KEYS)  # pasar paling akhir dilonggarkan: kripto dibandingkan dengan kripto dulu

HORIZON = 5


def analog_table(histories: Dict[str, pd.DataFrame], horizon: int = HORIZON) -> pd.DataFrame:
    """Semua hari dari semua simbol: bucket konteks + return `horizon` hari ke depan (%)."""
    parts = []
    for sym, raw in histories.items():
        if raw is None or len(raw) <= horizon + 1:
            continue
        f = feature_frame(raw)
        f["fwd"] = (raw["Close"].shift(-horizon) / raw["Close"] - 1) * 100
        f["symbol"] = sym
        f["pasar"] = market_of(sym)
        parts.append(f.dropna(subset=["fwd", *CANDLE_KEYS]))
    return pd.concat(parts) if parts else pd.DataFrame(columns=[*KEYS, "fwd", "symbol"])


def analog_stats(table: pd.DataFrame, ctx: dict, keys=KEYS, min_n: int = 30) -> Optional[dict]:
    """Statistik hasil ke depan untuk hari-hari dengan bucket sama. Bila sampel kurang, kunci dilonggarkan."""
    keys = [k for k in keys if ctx.get(k) is not None]
    while keys:
        mask = np.ones(len(table), dtype=bool)
        for k in keys:
            mask &= (table[k] == ctx[k]).to_numpy()
        sub = table.loc[mask, "fwd"].astype(float)
        if len(sub) >= min_n:
            return {
                "kunci": {k: ctx[k] for k in keys},
                "n": int(len(sub)),
                "simbol": int(table.loc[mask, "symbol"].nunique()),
                "median_return": round(float(sub.median()), 2),
                "rata_return": round(float(sub.mean()), 2),
                "peluang_naik": round(float((sub > 0).mean() * 100), 1),
                "p10": round(float(sub.quantile(0.1)), 2),
                "p90": round(float(sub.quantile(0.9)), 2),
                "horizon_hari": HORIZON,
            }
        keys = keys[:-1]  # longgarkan kunci paling akhir (paling spesifik)
    return None
