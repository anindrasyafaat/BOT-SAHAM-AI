"""
Screener Routes untuk Trading Command Center
API endpoints untuk market screening dan filtering
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from database.connection import get_db_session
from utils.logger import setup_logging

logger = setup_logging()
router = APIRouter()


@router.get("/gainers")
async def screen_gainers(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    min_change: float = Query(3.0, description="Minimum change percentage"),
    min_volume: Optional[float] = Query(None, description="Minimum volume"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Screen for top gainers"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "GOTO.JK",
                "name": "GoTo Gojek Tokopedia",
                "price": 125,
                "change": 15.5,
                "change_percent": 14.15,
                "volume": 250000000,
                "market_cap": 150000000000,
                "criteria_met": ["High Volume", "Strong Momentum", "Breakout"]
            },
            {
                "symbol": "TLKM.JK",
                "name": "Telkom Indonesia",
                "price": 4850,
                "change": 425,
                "change_percent": 9.6,
                "volume": 125000000,
                "market_cap": 480000000000,
                "criteria_met": ["Blue Chip", "Dividend Yield", "Technical Breakout"]
            },
            {
                "symbol": "ANTM.JK",
                "name": "Aneka Tambang",
                "price": 2850,
                "change": 225,
                "change_percent": 8.57,
                "volume": 87500000,
                "market_cap": 280000000000,
                "criteria_met": ["Commodity Play", "Volume Surge", "Trend Following"]
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "min_change": min_change,
                "min_volume": min_volume
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error screening gainers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/losers")
async def screen_losers(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    max_change: float = Query(-3.0, description="Maximum change percentage (negative)"),
    min_volume: Optional[float] = Query(None, description="Minimum volume"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Screen for top losers (potential reversal opportunities)"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "ADRO.JK",
                "name": "Adaro Energy",
                "price": 2850,
                "change": -225,
                "change_percent": -7.32,
                "volume": 150000000,
                "market_cap": 850000000000,
                "criteria_met": ["Oversold", "High Volume", "Support Level"],
                "reversal_potential": "High"
            },
            {
                "symbol": "ICBP.JK",
                "name": "Indofood CBP",
                "price": 8750,
                "change": -425,
                "change_percent": -4.63,
                "volume": 65000000,
                "market_cap": 420000000000,
                "criteria_met": ["Consumer Defensive", "Dividend Play", "Oversold"],
                "reversal_potential": "Medium"
            },
            {
                "symbol": "UNTR.JK",
                "name": "United Tractors",
                "price": 48500,
                "change": -2100,
                "change_percent": -4.15,
                "volume": 35000000,
                "market_cap": 2800000000000,
                "criteria_met": ["Heavy Equipment", "Commodity Correlation", "Support Zone"],
                "reversal_potential": "Medium"
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "max_change": max_change,
                "min_volume": min_volume
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error screening losers: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/volume-explosion")
async def screen_volume_explosion(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    min_volume_ratio: float = Query(2.0, description="Minimum volume ratio vs average"),
    min_price_change: float = Query(2.0, description="Minimum price change percentage"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Screen for volume explosion patterns"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "BMRI.JK",
                "name": "Bank Mandiri",
                "price": 7250,
                "change": 350,
                "change_percent": 5.07,
                "volume": 450000000,
                "avg_volume": 125000000,
                "volume_ratio": 3.6,
                "market_cap": 1650000000000,
                "criteria_met": ["Volume Explosion", "Price Breakout", "Institutional Interest"]
            },
            {
                "symbol": "PGAS.JK",
                "name": "Perusahaan Gas Negara",
                "price": 2850,
                "change": 185,
                "change_percent": 6.94,
                "volume": 325000000,
                "avg_volume": 85000000,
                "volume_ratio": 3.82,
                "market_cap": 680000000000,
                "criteria_met": ["Volume Surge", "Commodity Rally", "Technical Breakout"]
            },
            {
                "symbol": "PTBA.JK",
                "name": "Bukit Asam",
                "price": 3850,
                "change": 225,
                "change_percent": 6.21,
                "volume": 285000000,
                "avg_volume": 75000000,
                "volume_ratio": 3.8,
                "market_cap": 420000000000,
                "criteria_met": ["Coal Rally", "Volume Breakout", "Momentum Play"]
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "min_volume_ratio": min_volume_ratio,
                "min_price_change": min_price_change
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error screening volume explosion: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/breakouts")
async def screen_breakouts(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    min_breakout_strength: float = Query(3.0, description="Minimum breakout strength in percentage"),
    lookback_days: int = Query(52, description="Lookback period for 52-week high"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Screen for breakout patterns (52-week high breakouts)"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "ASII.JK",
                "name": "Astra International",
                "price": 7200,
                "change": 425,
                "change_percent": 6.27,
                "volume": 275000000,
                "week_52_high": 7150,
                "week_52_low": 4850,
                "breakout_strength": 6.27,
                "market_cap": 2800000000000,
                "criteria_met": ["52-Week High Breakout", "Volume Confirmation", "Strong Momentum"]
            },
            {
                "symbol": "KLBF.JK",
                "name": "Kalbe Farma",
                "price": 1680,
                "change": 85,
                "change_percent": 5.33,
                "volume": 185000000,
                "week_52_high": 1675,
                "week_52_low": 1245,
                "breakout_strength": 5.33,
                "market_cap": 820000000000,
                "criteria_met": ["52-Week High", "Healthcare Sector", "Dividend Aristocrat"]
            },
            {
                "symbol": "SMGR.JK",
                "name": "Semen Indonesia",
                "price": 10250,
                "change": 550,
                "change_percent": 5.67,
                "volume": 145000000,
                "week_52_high": 10200,
                "week_52_low": 7850,
                "breakout_strength": 5.67,
                "market_cap": 1560000000000,
                "criteria_met": ["Infrastructure Play", "52-Week High Breakout", "Volume Spike"]
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "min_breakout_strength": min_breakout_strength,
                "lookback_days": lookback_days
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error screening breakouts: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/oversold")
async def screen_oversold(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    max_rsi: float = Query(30.0, description="Maximum RSI level for oversold"),
    min_volume: Optional[float] = Query(None, description="Minimum volume"),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_db_session)
):
    """Screen for oversold conditions (potential mean reversion)"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "MIKA.JK",
                "name": "Mitra Keluarga",
                "price": 1580,
                "change": -45,
                "change_percent": -2.77,
                "volume": 85000000,
                "rsi": 28.5,
                "market_cap": 235000000000,
                "criteria_met": ["Oversold RSI", "Healthcare Defensive", "Support Level"],
                "mean_reversion_potential": "High"
            },
            {
                "symbol": "SIDO.JK",
                "name": "Indofood Sukses Makmur",
                "price": 485,
                "change": -15,
                "change_percent": -3.0,
                "volume": 125000000,
                "rsi": 26.8,
                "market_cap": 420000000000,
                "criteria_met": ["Oversold", "Consumer Staples", "Dividend Yield"],
                "mean_reversion_potential": "Medium"
            },
            {
                "symbol": "GGRM.JK",
                "name": "Gudang Garam",
                "price": 28500,
                "change": -1200,
                "change_percent": -4.04,
                "volume": 35000000,
                "rsi": 24.2,
                "market_cap": 580000000000,
                "criteria_met": ["Extremely Oversold", "Sin Stock", "High Dividend"],
                "mean_reversion_potential": "High"
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "max_rsi": max_rsi,
                "min_volume": min_volume
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error screening oversold: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/custom")
async def custom_screen(
    market_type: str = Query("all", regex="^(all|indonesia|us|crypto)$"),
    min_price: Optional[float] = Query(None, description="Minimum price"),
    max_price: Optional[float] = Query(None, description="Maximum price"),
    min_volume: Optional[float] = Query(None, description="Minimum volume"),
    min_market_cap: Optional[float] = Query(None, description="Minimum market cap"),
    min_change: Optional[float] = Query(None, description="Minimum change percentage"),
    max_change: Optional[float] = Query(None, description="Maximum change percentage"),
    limit: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_db_session)
):
    """Custom screening dengan multiple criteria"""
    try:
        # Mock screening results untuk demo
        results = [
            {
                "symbol": "ACES.JK",
                "name": "Ace Hardware Indonesia",
                "price": 1450,
                "change": 35,
                "change_percent": 2.47,
                "volume": 95000000,
                "market_cap": 285000000000,
                "pe_ratio": 18.5,
                "pb_ratio": 2.1,
                "dividend_yield": 2.8,
                "criteria_met": [
                    "Retail Play",
                    "Consumer Discretionary",
                    "Growth Stock",
                    "Dividend Paying"
                ]
            },
            {
                "symbol": "AMRT.JK",
                "name": "Sumber Alfaria Trijaya",
                "price": 875,
                "change": 25,
                "change_percent": 2.94,
                "volume": 185000000,
                "market_cap": 165000000000,
                "pe_ratio": 22.3,
                "pb_ratio": 3.8,
                "dividend_yield": 1.5,
                "criteria_met": [
                    "Retail Giant",
                    "Consumer Staples",
                    "Defensive Play",
                    "High Volume"
                ]
            }
        ]
        
        return {
            "status": "success",
            "data": results,
            "total": len(results),
            "criteria": {
                "market_type": market_type,
                "min_price": min_price,
                "max_price": max_price,
                "min_volume": min_volume,
                "min_market_cap": min_market_cap,
                "min_change": min_change,
                "max_change": max_change
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Error custom screening: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")