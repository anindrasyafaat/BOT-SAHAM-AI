"""
News Routes: berita nyata dari Yahoo Finance + skor sentimen (news_sentiment/analyzer.py).
"""

from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Query

from news_sentiment.analyzer import MARKET_QUERIES, SentimentAnalyzer

router = APIRouter()
analyzer = SentimentAnalyzer()
CATEGORY = {"stock market": "Pasar Global", "Indonesia stocks": "Pasar Indonesia", "bitcoin crypto": "Kripto"}


def _with_category(items):
    return [{**n, "category": CATEGORY.get(n["query"], "Emiten"), "symbol": (n["related"] or [None])[0]} for n in items]


@router.get("/latest")
async def get_latest_news(limit: int = Query(20, ge=1, le=100), category: Optional[str] = Query(None)):
    items = _with_category(await analyzer.get_news(None, 15))
    if category:
        items = [n for n in items if n["category"] == category]
    return {"status": "success", "data": items[:limit], "total": len(items)}


@router.get("/sentiment")
async def get_sentiment_analysis(symbol: Optional[str] = Query(None), days: int = Query(7, ge=1, le=30)):
    items = await analyzer.get_news(symbol, 25) if symbol else await analyzer.get_news(None, 25)
    start = date.today() - timedelta(days=days - 1)
    by_day = defaultdict(list)
    for n in items:
        d = datetime.fromisoformat(n["published_at"]).date()
        if d >= start:
            by_day[d].append(n)
    timeline = []
    for i in range(days):
        d = start + timedelta(days=i)
        day = by_day.get(d, [])
        labels = Counter(n["sentiment"] for n in day)
        timeline.append({
            "date": d.isoformat(),
            "sentiment_score": sum(n["sentiment_score"] for n in day) / len(day) if day else None,
            "news_count": len(day), "positive_news": labels["positive"],
            "negative_news": labels["negative"], "neutral_news": labels["neutral"],
        })
    scored = [n for v in by_day.values() for n in v]
    avg = sum(n["sentiment_score"] for n in scored) / len(scored) if scored else 0.0
    return {"status": "success", "data": {
        "summary": {"overall_sentiment": avg,
                    "sentiment_label": "positive" if avg > 0.1 else "negative" if avg < -0.1 else "neutral",
                    "total_news": len(scored), "period_days": days, "symbol": symbol},
        "timeline": timeline,
    }}


@router.get("/by-symbol/{symbol}")
async def get_news_by_symbol(symbol: str, limit: int = Query(10, ge=1, le=50)):
    query = symbol[:-4] + "-USD" if symbol.upper().endswith("USDT") else symbol
    items = _with_category(await analyzer.get_news(query, limit))
    return {"status": "success", "data": items, "total": len(items), "symbol": symbol}


@router.get("/categories")
async def get_news_categories():
    counts = Counter(n["category"] for n in _with_category(await analyzer.get_news(None, 15)))
    return {"status": "success", "data": [{"name": CATEGORY[q], "count": counts.get(CATEGORY[q], 0)} for q in MARKET_QUERIES]}


@router.get("/high-impact")
async def get_high_impact_news(limit: int = Query(10, ge=1, le=50)):
    items = [n for n in _with_category(await analyzer.get_news(None, 15)) if n["impact"] == "high"]
    return {"status": "success", "data": items[:limit], "total": len(items)}
