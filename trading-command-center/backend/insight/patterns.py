"""
Penambangan pola dari pengalaman sinyal tertutup: kondisi mana yang berulang kali berhasil / gagal.
Batas bawah Wilson dipakai agar pola dengan sampel kecil tidak terlihat lebih meyakinkan dari kenyataannya.
"""

import math
from collections import defaultdict
from itertools import combinations
from typing import Iterable, List

FEATURES = ("regime", "rsi", "volatilitas", "volume", "pasar", "fear_greed", "sentimen")
MIN_N = 8


def wilson(wins: int, n: int, z: float = 1.96) -> tuple:
    """Interval Wilson 95% untuk proporsi menang."""
    if n == 0:
        return 0.0, 1.0
    p = wins / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return max(0.0, center - half), min(1.0, center + half)


def _keys(rec: dict) -> Iterable[tuple]:
    ctx = rec.get("context") or {}
    items = [("strategi", rec["strategy"])] + [(f, ctx[f]) for f in FEATURES if ctx.get(f) is not None]
    for it in items:
        yield (it,)
    for a, b in combinations(items, 2):
        yield (a, b)


def mine(records: List[dict], min_n: int = MIN_N, top: int = 8) -> dict:
    """records: {strategy, pnl (persen), context}. Kembalikan pola berhasil & gagal."""
    groups = defaultdict(list)
    for r in records:
        if r.get("pnl") is None:
            continue
        for k in _keys(r):
            groups[k].append(float(r["pnl"]))
    rows = []
    for k, pnls in groups.items():
        n = len(pnls)
        if n < min_n:
            continue
        wins = sum(p > 0 for p in pnls)
        lo, hi = wilson(wins, n)
        rows.append({
            "kondisi": {a: b for a, b in k}, "n": n, "win_rate": round(wins / n * 100, 1),
            "expectancy": round(sum(pnls) / n, 3), "wilson_bawah": round(lo * 100, 1), "wilson_atas": round(hi * 100, 1),
        })
    good = sorted((r for r in rows if r["expectancy"] > 0), key=lambda r: (-r["wilson_bawah"], -r["expectancy"]))
    bad = sorted((r for r in rows if r["expectancy"] < 0), key=lambda r: (r["wilson_atas"], r["expectancy"]))
    return {"berhasil": good[:top], "gagal": bad[:top], "total_pengalaman": sum(1 for r in records if r.get("pnl") is not None)}


def matching(patterns: dict, ctx: dict, strategy: str = None) -> dict:
    """Pola yang semua kondisinya cocok dengan konteks sekarang (opsional: strategi tertentu)."""
    def fits(p):
        for k, v in p["kondisi"].items():
            if k == "strategi":
                if strategy is not None and v != strategy:
                    return False
            elif ctx.get(k) != v:
                return False
        return True
    return {"berhasil": [p for p in patterns["berhasil"] if fits(p)], "gagal": [p for p in patterns["gagal"] if fits(p)]}
