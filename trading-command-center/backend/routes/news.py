"""
News Routes untuk Trading Command Center
API endpoints untuk news dan sentiment analysis
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from database.connection import get_db_session
from utils.logger import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/latest")
async def get_latest_news(
    limit: int = Query(20, ge=1, le=100),
    category: Optional[str] = Query(None, description="News category"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get latest market news"""
    try:
        # Mock news data untuk demo
        news_data = [
            {
                "id": "news_001",
                "title": "Bank Indonesia Pertahankan Suku Bunga Acuan di 6%",
                "summary": "Bank Indonesia memutuskan untuk mempertahankan suku bunga acuan BI-Rate pada level 6% dalam rapat dewan gubernur bulan ini.",
                "content": "Keputusan ini diambil untuk menjaga stabilitas nilai tukar rupiah dan mengendalikan inflasi yang masih dalam target range.",
                "source": "Bisnis.com",
                "category": "Monetary Policy",
                "published_at": "2024-01-27T14:30:00Z",
                "symbol": "BI",
                "sentiment": "neutral",
                "sentiment_score": 0.05,
                "impact": "medium",
                "url": "https://example.com/news/bi-rate"
            },
            {
                "id": "news_002",
                "title": "Harga Batubara Meningkat 15% Didorong Permintaan Tiongkok",
                "summary": "Harga batubara thermal global melonjak 15% dalam seminggu terakhir didorong permintaan kuat dari Tiongkok dan cuaca ekstrem di Australia.",
                "content": "Kenaikan harga ini berdampak positif pada emiten batubara Indonesia seperti ADRO, PTBA, dan ITMG yang melihat potensi peningkatan margin.",
                "source": "CNBC Indonesia",
                "category": "Commodities",
                "published_at": "2024-01-27T12:15:00Z",
                "symbol": "ADRO.JK",
                "sentiment": "positive",
                "sentiment_score": 0.75,
                "impact": "high",
                "url": "https://example.com/news/coal-price"
            },
            {
                "id": "news_003",
                "title": "Fitch Reaffirms Indonesia's BBB Rating with Stable Outlook",
                "summary": "Lembaga pemeringkat Fitch Ratings menegaskan kembali peringkat BBB untuk Indonesia dengan outlook stabil.",
                "content": "Peringkat ini mencerminkan fundamental ekonomi Indonesia yang solid, termasuk pertumbuhan ekonomi yang kuat dan manajemen fiskal yang baik.",
                "source": "Reuters",
                "category": "Credit Rating",
                "published_at": "2024-01-27T10:45:00Z",
                "symbol": "ID",
                "sentiment": "positive",
                "sentiment_score": 0.65,
                "impact": "high",
                "url": "https://example.com/news/fitch-rating"
            },
            {
                "id": "news_004",
                "title": "GoTo (GOTO) Targetkan EBITDA Positif pada Akhir 2024",
                "summary": "PT GoTo Gojek Tokopedia Tbk menargetkan EBITDA positif pada akhir tahun 2024 melalui efisiensi operasional dan pertumbuhan bisnis.",
                "content": "Manajemen GoTo optimis dapat mencapai target ini dengan strategi yang fokus pada profitabilitas dan pengendalian biaya operasional.",
                "source": "Kontan",
                "category": "Corporate",
                "published_at": "2024-01-27T09:20:00Z",
                "symbol": "GOTO.JK",
                "sentiment": "positive",
                "sentiment_score": 0.55,
                "impact": "medium",
                "url": "https://example.com/news/goto-ebitda"
            },
            {
                "id": "news_005",
                "title": "IHSG Ditutup Menguat 0.8% Didorong Sektor Perbankan",
                "summary": "Indeks Harga Saham Gabungan (IHSG) ditutup menguat 0.8% pada perdagangan hari ini didorong penguatan sektor perbankan dan consumer goods.",
                "content": "Sektor perbankan menjadi penyumbang kenaikan terbesar dengan BBRI dan BBCA naik lebih dari 2% masing-masing.",
                "source": "IDX Channel",
                "category": "Market Summary",
                "published_at": "2024-01-26T16:15:00Z",
                "symbol": "IHSG",
                "sentiment": "positive",
                "sentiment_score": 0.45,
                "impact": "medium",
                "url": "https://example.com/news/ihsg-summary"
            }
        ]
        
        # Apply category filter if specified
        if category:
            news_data = [news for news in news_data if news["category"] == category]
        
        # Apply limit
        news_data = news_data[:limit]
        
        return {
            "status": "success",
            "data": news_data,
            "total": len(news_data),
            "category": category
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting latest news: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/sentiment")
async def get_sentiment_analysis(
    symbol: Optional[str] = Query(None, description="Filter by symbol"),
    days: int = Query(7, ge=1, le=30, description="Number of days to analyze"),
    session: AsyncSession = Depends(get_db_session)
):
    """Get sentiment analysis untuk market news"""
    try:
        # Mock sentiment data untuk demo
        import datetime
        
        base_date = datetime.datetime.now() - datetime.timedelta(days=days)
        sentiment_timeline = []
        
        for i in range(days):
            date = base_date + datetime.timedelta(days=i)
            
            # Mock sentiment data dengan random walk
            import random
            base_sentiment = 0.1
            daily_sentiment = base_sentiment + random.uniform(-0.3, 0.4)
            daily_sentiment = max(-1, min(1, daily_sentiment))  # Clamp to [-1, 1]
            
            sentiment_timeline.append({
                "date": date.isoformat(),
                "sentiment_score": daily_sentiment,
                "sentiment_label": "positive" if daily_sentiment > 0.1 else "negative" if daily_sentiment < -0.1 else "neutral",
                "news_count": random.randint(5, 25),
                "positive_news": random.randint(1, 15),
                "negative_news": random.randint(1, 10),
                "neutral_news": random.randint(1, 8)
            })
        
        # Calculate overall sentiment
        avg_sentiment = sum(item["sentiment_score"] for item in sentiment_timeline) / len(sentiment_timeline)
        total_news = sum(item["news_count"] for item in sentiment_timeline)
        
        summary = {
            "overall_sentiment": avg_sentiment,
            "sentiment_label": "positive" if avg_sentiment > 0.1 else "negative" if avg_sentiment < -0.1 else "neutral",
            "total_news": total_news,
            "period_days": days,
            "symbol": symbol
        }
        
        return {
            "status": "success",
            "data": {
                "summary": summary,
                "timeline": sentiment_timeline
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/by-symbol/{symbol}")
async def get_news_by_symbol(
    symbol: str,
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session)
):
    """Get news specific untuk symbol"""
    try:
        # Mock news data untuk specific symbol
        news_data = [
            {
                "id": f"news_{symbol}_001",
                "title": f"{symbol} Meningkat 5% Didorong Volume Tinggi",
                "summary": f"Saham {symbol} mengalami kenaikan 5% dalam perdagangan hari ini dengan volume yang signifikan.",
                "content": "Analis mengatakan kenaikan ini didorong oleh sentimen positif dan tekanan beli dari investor institusional.",
                "source": "Market Watch",
                "category": "Stock Movement",
                "published_at": "2024-01-27T11:30:00Z",
                "symbol": symbol,
                "sentiment": "positive",
                "sentiment_score": 0.65,
                "impact": "medium",
                "url": f"https://example.com/news/{symbol.lower()}"
            },
            {
                "id": f"news_{symbol}_002",
                "title": f"Analis: {symbol} Masih Punya Potensi Kenaikan",
                "summary": f"Beberapa analis melihat {symbol} masih memiliki potensi kenaikan jangka menengah.",
                "content": "Dengan fundamental yang solid dan prospek bisnis yang positif, saham ini menarik untuk dipertimbangkan.",
                "source": "Investor Daily",
                "category": "Analysis",
                "published_at": "2024-01-26T14:20:00Z",
                "symbol": symbol,
                "sentiment": "positive",
                "sentiment_score": 0.45,
                "impact": "low",
                "url": f"https://example.com/news/{symbol.lower()}-analysis"
            }
        ]
        
        return {
            "status": "success",
            "data": news_data,
            "total": len(news_data),
            "symbol": symbol
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting news for {symbol}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/categories")
async def get_news_categories(session: AsyncSession = Depends(get_db_session)):
    """Get available news categories"""
    try:
        categories = [
            {"name": "Market Summary", "count": 156},
            {"name": "Corporate", "count": 89},
            {"name": "Monetary Policy", "count": 23},
            {"name": "Commodities", "count": 67},
            {"name": "Credit Rating", "count": 12},
            {"name": "Economic Data", "count": 45},
            {"name": "IPO", "count": 8},
            {"name": "Regulation", "count": 34}
        ]
        
        return {
            "status": "success",
            "data": categories,
            "total": len(categories)
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting news categories: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/high-impact")
async def get_high_impact_news(
    limit: int = Query(10, ge=1, le=50),
    session: AsyncSession = Depends(get_db_session)
):
    """Get high impact news yang dapat mempengaruhi market"""
    try:
        # Mock high impact news
        high_impact_news = [
            {
                "id": "hi_news_001",
                "title": "Fed Menahan Suku Bunga dan Sinyalkan Potensi Penurunan",
                "summary": "The Federal Reserve mempertahankan suku bunga dan memberikan sinyal potensi penurunan suku bunga dalam pertemuan FOMC.",
                "impact": "high",
                "sentiment": "positive",
                "sentiment_score": 0.85,
                "symbols_affected": ["USD", "SPY", "QQQ", "GLD"],
                "published_at": "2024-01-27T20:00:00Z",
                "category": "Monetary Policy",
                "source": "Federal Reserve"
            },
            {
                "id": "hi_news_002",
                "title": "OPEC+ Umumkan Potensi Pengurangan Produksi Minyak",
                "summary": "OPEC+ mengumumkan kemungkinan pengurangan produksi minyak untuk menstabilkan harga minyak global.",
                "impact": "high",
                "sentiment": "positive",
                "sentiment_score": 0.72,
                "symbols_affected": ["CL", "XOM", "CVX", "USO"],
                "published_at": "2024-01-27T16:30:00Z",
                "category": "Commodities",
                "source": "OPEC"
            },
            {
                "id": "hi_news_003",
                "title": "BI Pertahankan Suku Bunga, Rupiah Menguat",
                "summary": "Bank Indonesia mempertahankan suku bunga acuan di 6%, mendorong penguatan rupiah terhadap dollar AS.",
                "impact": "high",
                "sentiment": "positive",
                "sentiment_score": 0.68,
                "symbols_affected": ["USDIDR", "IHSG", "BBRI", "BBCA"],
                "published_at": "2024-01-27T14:00:00Z",
                "category": "Monetary Policy",
                "source": "Bank Indonesia"
            }
        ]
        
        return {
            "status": "success",
            "data": high_impact_news[:limit],
            "total": len(high_impact_news),
            "limit": limit
        }
        
    except Exception as e:
        logger.error(f"❌ Error getting high impact news: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")