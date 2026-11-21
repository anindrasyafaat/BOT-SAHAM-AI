"""
Berita pasar dari Yahoo Finance (endpoint search) + skor sentimen berbasis leksikon (Inggris & Indonesia).

shortcut: leksikon sederhana, bukan model NLP; ganti dengan model (mis. FinBERT) bila butuh akurasi lebih.
"""

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import yfinance as yf

from utils.logger import setup_logging

logger = setup_logging()

POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains", "jump", "jumps",
    "record", "upgrade", "upgrades", "bullish", "growth", "profit", "profits", "strong", "outperform", "rise",
    "rises", "rebound", "boost", "buy", "approval", "dividend", "expansion", "high", "higher", "win", "wins",
    "naik", "melonjak", "menguat", "laba", "untung", "tumbuh", "rekor", "positif", "dividen", "ekspansi",
}
NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "slump", "slumps", "fall", "falls", "drop", "drops", "crash",
    "downgrade", "downgrades", "bearish", "loss", "losses", "weak", "underperform", "decline", "declines",
    "lawsuit", "probe", "fraud", "default", "cut", "cuts", "layoffs", "warning", "low", "lower", "sell",
    "selloff", "worst", "fear", "risk", "slide", "slides", "tumble", "tumbles", "collapse",
    "turun", "anjlok", "melemah", "rugi", "merosot", "negatif", "gagal", "krisis", "terendah",
}
WORD = re.compile(r"[a-zA-Z]+")
MARKET_QUERIES = ["stock market", "Indonesia stocks", "bitcoin crypto"]
CACHE_TTL = 900


def score_text(text: str) -> Tuple[float, str]:
    """Skor -1..1 dan label positive/negative/neutral."""
    words = [w.lower() for w in WORD.findall(text)]
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    score = 0.0 if pos + neg == 0 else (pos - neg) / (pos + neg)
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return score, label


def _search_news(query: str, count: int) -> List[dict]:
    items = []
    for n in yf.Search(query, news_count=count, max_results=1).news:
        score, label = score_text(n.get("title", ""))
        items.append({
            "id": n.get("uuid"),
            "title": n.get("title", ""),
            "summary": n.get("title", ""),
            "source": n.get("publisher", "Yahoo Finance"),
            "url": n.get("link"),
            "published_at": datetime.fromtimestamp(n.get("providerPublishTime", 0), tz=timezone.utc).isoformat(),
            "related": n.get("relatedTickers", []),
            "query": query,
            "sentiment": label,
            "sentiment_score": round(score, 3),
            "impact": "high" if abs(score) >= 0.5 else "medium" if abs(score) > 0 else "low",
        })
    return items


class SentimentAnalyzer:
    """Ambil & cache berita lalu hitung sentimennya."""

    _cache: Dict[str, Tuple[float, List[dict]]] = {}  # dibagi semua instance: hemat kuota Yahoo

    async def get_news(self, query: Optional[str] = None, count: int = 10) -> List[dict]:
        if query is None:
            batches = await asyncio.gather(*(self.get_news(q, count) for q in MARKET_QUERIES))
            merged = {n["id"]: n for b in batches for n in b}
            return sorted(merged.values(), key=lambda n: n["published_at"], reverse=True)
        key = f"{query}:{count}"
        hit = self._cache.get(key)
        if hit and time.time() - hit[0] < CACHE_TTL:
            return hit[1]
        try:
            items = await asyncio.to_thread(_search_news, query, count)
        except Exception as e:
            logger.warning(f"⚠️ News fetch '{query}': {e}")
            return hit[1] if hit else []
        self._cache[key] = (time.time(), items)
        return items

    async def get_news_sentiment(self, symbol: str) -> Optional[float]:
        query = symbol[:-4] + "-USD" if symbol.endswith("USDT") else symbol
        news = await self.get_news(query, 10)
        if not news:
            return None  # tanpa berita, jangan mengarang sentimen
        return sum(n["sentiment_score"] for n in news) / len(news)

    async def get_social_sentiment(self, symbol: str) -> Optional[float]:
        return None  # belum ada sumber media sosial
