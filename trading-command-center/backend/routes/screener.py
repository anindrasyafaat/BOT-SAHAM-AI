"""
Screener Routes: dihitung dari data pasar terbaru + candle harian (market_data/manager.py).
"""

from typing import Callable, List, Optional

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

router = APIRouter()
MARKET = Query("all", pattern="^(all|indonesia|us|crypto)$")


def rsi(closes: pd.Series, length: int = 14) -> Optional[float]:
    """RSI Wilder."""
    if len(closes) <= length:
        return None
    delta = closes.diff()
    gain = delta.clip(lower=0).ewm(alpha=1 / length, adjust=False).mean()
    loss = (-delta.clip(upper=0)).ewm(alpha=1 / length, adjust=False).mean()
    last_loss = float(loss.iloc[-1])
    return 100.0 if last_loss == 0 else float(100 - 100 / (1 + gain.iloc[-1] / last_loss))


def _rows(request: Request, market_type: str) -> List[dict]:
    mdm = getattr(request.app.state, "market_data_manager", None)
    if mdm is None:
        raise HTTPException(status_code=503, detail="Market data belum siap")
    out = []
    for sym, q in mdm.get_all_market_data().items():
        if market_type != "all" and mdm.market_type_of.get(sym) != market_type:
            continue
        hist = mdm.history.get(sym)
        vol_avg = q.get("volume_avg") or 0
        out.append({
            "symbol": sym, "name": q.get("name", sym), "market": mdm.market_type_of.get(sym),
            "price": q["current_price"], "change": q["change_amount"], "change_percent": q["change_percent"],
            "volume": q.get("volume") or 0, "avg_volume": vol_avg,
            "volume_ratio": (q.get("volume") or 0) / vol_avg if vol_avg else None,
            "market_cap": q.get("market_cap"),
            "fifty_two_week_high": q.get("fifty_two_week_high"),
            "rsi": rsi(hist["Close"]) if hist is not None else None,
            "_hist": hist,
        })
    return out


def _respond(rows: List[dict], keep: Callable[[dict], bool], key: Callable[[dict], float],
             criteria: Callable[[dict], List[str]], limit: int, params: dict, reverse=True):
    hits = sorted((r for r in rows if keep(r)), key=key, reverse=reverse)[:limit]
    data = [{**{k: v for k, v in r.items() if k != "_hist"}, "criteria_met": criteria(r)} for r in hits]
    return {"status": "success", "data": data, "total": len(data), "criteria": params}


def _vol_ok(r, min_volume):
    return min_volume is None or r["volume"] >= min_volume


@router.get("/gainers")
async def screen_gainers(request: Request, market_type: str = MARKET, min_change: float = Query(3.0),
                         min_volume: Optional[float] = Query(None), limit: int = Query(20, ge=1, le=100)):
    return _respond(_rows(request, market_type),
                    lambda r: r["change_percent"] >= min_change and _vol_ok(r, min_volume),
                    lambda r: r["change_percent"],
                    lambda r: [f"Naik {r['change_percent']:.1f}%"] + (["Volume tinggi"] if (r["volume_ratio"] or 0) >= 1.5 else []),
                    limit, {"market_type": market_type, "min_change": min_change, "min_volume": min_volume})


@router.get("/losers")
async def screen_losers(request: Request, market_type: str = MARKET, max_change: float = Query(-3.0),
                        min_volume: Optional[float] = Query(None), limit: int = Query(20, ge=1, le=100)):
    return _respond(_rows(request, market_type),
                    lambda r: r["change_percent"] <= max_change and _vol_ok(r, min_volume),
                    lambda r: r["change_percent"],
                    lambda r: [f"Turun {r['change_percent']:.1f}%"] + (["Volume tinggi"] if (r["volume_ratio"] or 0) >= 1.5 else []),
                    limit, {"market_type": market_type, "max_change": max_change, "min_volume": min_volume},
                    reverse=False)


@router.get("/volume-explosion")
async def screen_volume_explosion(request: Request, market_type: str = MARKET,
                                  min_volume_ratio: float = Query(2.0), min_price_change: float = Query(2.0),
                                  limit: int = Query(20, ge=1, le=100)):
    return _respond(_rows(request, market_type),
                    lambda r: (r["volume_ratio"] or 0) >= min_volume_ratio and abs(r["change_percent"]) >= min_price_change,
                    lambda r: r["volume_ratio"] or 0,
                    lambda r: [f"Volume {r['volume_ratio']:.1f}× rata-rata 20 hari", f"Harga {r['change_percent']:+.1f}%"],
                    limit, {"market_type": market_type, "min_volume_ratio": min_volume_ratio,
                            "min_price_change": min_price_change})


@router.get("/breakouts")
async def screen_breakouts(request: Request, market_type: str = MARKET,
                           lookback_days: int = Query(20, ge=5, le=250), limit: int = Query(20, ge=1, le=100)):
    def prior_high(r):
        h = r["_hist"]
        return float(h["High"].iloc[-lookback_days - 1:-1].max()) if h is not None and len(h) > lookback_days else None

    def keep(r):
        ph = prior_high(r)
        r["breakout_level"] = ph
        r["breakout_strength"] = (r["price"] / ph - 1) * 100 if ph else None
        return ph is not None and r["price"] > ph

    return _respond(_rows(request, market_type), keep, lambda r: r["breakout_strength"],
                    lambda r: [f"Tembus high {lookback_days} hari ({r['breakout_level']:.4g})",
                               f"+{r['breakout_strength']:.1f}% di atas level"]
                    + (["Volume konfirmasi"] if (r["volume_ratio"] or 0) >= 1.5 else []),
                    limit, {"market_type": market_type, "lookback_days": lookback_days})


@router.get("/oversold")
async def screen_oversold(request: Request, market_type: str = MARKET, max_rsi: float = Query(30.0),
                          min_volume: Optional[float] = Query(None), limit: int = Query(20, ge=1, le=100)):
    return _respond(_rows(request, market_type),
                    lambda r: r["rsi"] is not None and r["rsi"] <= max_rsi and _vol_ok(r, min_volume),
                    lambda r: r["rsi"], lambda r: [f"RSI(14) {r['rsi']:.1f}"],
                    limit, {"market_type": market_type, "max_rsi": max_rsi, "min_volume": min_volume}, reverse=False)


@router.get("/custom")
async def custom_screen(request: Request, market_type: str = MARKET,
                        min_price: Optional[float] = None, max_price: Optional[float] = None,
                        min_volume: Optional[float] = None, min_market_cap: Optional[float] = None,
                        min_change: Optional[float] = None, max_change: Optional[float] = None,
                        limit: int = Query(50, ge=1, le=200)):
    def keep(r):
        return all([
            min_price is None or r["price"] >= min_price, max_price is None or r["price"] <= max_price,
            _vol_ok(r, min_volume), min_market_cap is None or (r["market_cap"] or 0) >= min_market_cap,
            min_change is None or r["change_percent"] >= min_change,
            max_change is None or r["change_percent"] <= max_change,
        ])
    return _respond(_rows(request, market_type), keep, lambda r: r["change_percent"], lambda r: ["Custom"],
                    limit, {"market_type": market_type})
