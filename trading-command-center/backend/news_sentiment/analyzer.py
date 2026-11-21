"""
Berita pasar + skor sentimen berbasis leksikon (Inggris & Indonesia). Semua sumber gratis tanpa API key:
- Yahoo Finance search: pasar global & kripto
- Google News RSS: saham IDX & IHSG (Yahoo hampir tidak punya berita emiten Indonesia)

shortcut: leksikon sederhana, bukan model NLP; ganti dengan model (mis. FinBERT) bila butuh akurasi lebih.
"""

import asyncio
import re
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import httpx
import yfinance as yf

from utils.logger import setup_logging

logger = setup_logging()

POSITIVE = {
    "beat", "beats", "surge", "surges", "soar", "soars", "rally", "rallies", "gain", "gains", "jump", "jumps",
    "record", "upgrade", "upgrades", "bullish", "growth", "profit", "profits", "strong", "outperform", "rise",
    "rises", "rebound", "boost", "buy", "approval", "dividend", "expansion", "high", "higher", "win", "wins",
    "naik", "melonjak", "menguat", "laba", "untung", "tumbuh", "rekor", "positif", "dividen", "ekspansi",
    "cuan", "menghijau", "melesat", "meroket", "akumulasi", "borong",
}
NEGATIVE = {
    "miss", "misses", "plunge", "plunges", "slump", "slumps", "fall", "falls", "drop", "drops", "crash",
    "downgrade", "downgrades", "bearish", "loss", "losses", "weak", "underperform", "decline", "declines",
    "lawsuit", "probe", "fraud", "default", "cut", "cuts", "layoffs", "warning", "low", "lower", "sell",
    "selloff", "worst", "fear", "risk", "slide", "slides", "tumble", "tumbles", "collapse",
    "turun", "anjlok", "melemah", "rugi", "merosot", "negatif", "gagal", "krisis", "terendah",
    "ambles", "ambruk", "jeblok", "susut", "memerah", "terkoreksi", "tertekan", "lesu",
}
WORD = re.compile(r"[a-zA-Z]+")
MARKET_QUERIES = ["stock market", "IHSG saham", "bitcoin crypto"]
GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"


def use_google_news(query: str) -> bool:
    return query.upper().endswith(".JK") or query == "IHSG saham"
CACHE_TTL = 900


def score_text(text: str) -> Tuple[float, str]:
    """Skor -1..1 dan label positive/negative/neutral."""
    words = [w.lower() for w in WORD.findall(text)]
    pos = sum(w in POSITIVE for w in words)
    neg = sum(w in NEGATIVE for w in words)
    score = 0.0 if pos + neg == 0 else (pos - neg) / (pos + neg)
    label = "positive" if score > 0.1 else "negative" if score < -0.1 else "neutral"
    return score, label


def _item(id_, title, source, url, published_at, related, query):
    score, label = score_text(title)
    return {
        "id": id_, "title": title, "summary": title, "source": source, "url": url,
        "published_at": published_at, "related": related, "query": query,
        "sentiment": label, "sentiment_score": round(score, 3),
        "impact": "high" if abs(score) >= 0.5 else "medium" if abs(score) > 0 else "low",
    }


def parse_google_rss(xml_text: str, query: str, related: List[str], count: int) -> List[dict]:
    root = ET.fromstring(xml_text)
    items = []
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        source = it.findtext("source") or "Google News"
        if title.endswith(f" - {source}"):  # Google menempelkan nama media di judul
            title = title[: -len(source) - 3]
        try:
            published = parsedate_to_datetime(it.findtext("pubDate")).astimezone(timezone.utc).isoformat()
        except (TypeError, ValueError):
            continue
        items.append(_item(it.findtext("guid") or it.findtext("link"), title, source, it.findtext("link"),
                           published, related, query))
        if len(items) >= count:
            break
    return items


def _google_news(query: str, count: int) -> List[dict]:
    is_symbol = query.upper().endswith(".JK")
    q = f"{query[:-3]} saham" if is_symbol else query
    r = httpx.get(GOOGLE_NEWS_RSS, params={"q": q, "hl": "id", "gl": "ID", "ceid": "ID:id"},
                  headers={"User-Agent": "Mozilla/5.0 TradingCommandCenter"}, timeout=15, follow_redirects=True)
    r.raise_for_status()
    return parse_google_rss(r.text, query, [query.upper()] if is_symbol else [], count)


def _search_news(query: str, count: int) -> List[dict]:
    if use_google_news(query):
        return _google_news(query, count)
    items = []
    for n in yf.Search(query, news_count=count, max_results=1).news:
        items.append(_item(n.get("uuid"), n.get("title", ""), n.get("publisher", "Yahoo Finance"), n.get("link"),
                           datetime.fromtimestamp(n.get("providerPublishTime", 0), tz=timezone.utc).isoformat(),
                           n.get("relatedTickers", []), query))
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
