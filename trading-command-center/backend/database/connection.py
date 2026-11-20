"""
Database Connection Manager untuk Trading Command Center
Menangani koneksi database dan session management
"""

import asyncio
from typing import AsyncGenerator
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base, sessionmaker
from config import get_database_url, settings
from utils.logger import setup_logging

logger = setup_logging()

# Database URL
DATABASE_URL = get_database_url()

# SQLAlchemy setup untuk SQLite async
if DATABASE_URL.startswith("sqlite"):
    # SQLite async support
    engine = create_async_engine(
        DATABASE_URL.replace("sqlite://", "sqlite+aiosqlite://"),
        echo=settings.debug,
        connect_args={"check_same_thread": False}
    )
else:
    # Untuk database lain (PostgreSQL, MySQL, dll)
    engine = create_async_engine(
        DATABASE_URL,
        echo=settings.debug,
        pool_size=20,
        max_overflow=0,
        pool_pre_ping=True
    )

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# Base class untuk models
Base = declarative_base()


async def init_database() -> None:
    """Inisialisasi database dan create tables"""
    try:
        async with engine.begin() as conn:
            # Import semua models
            from models.market_data import MarketData
            from models.signals import TradingSignal
            from models.portfolio import Portfolio, Position, Trade
            from models.news import NewsArticle, Sentiment
            from models.screener import ScreenerResult
            
            # Create semua tables
            await conn.run_sync(Base.metadata.create_all)
            
        logger.info("✅ Database tables created successfully")
        
    except Exception as e:
        logger.error(f"❌ Database initialization error: {e}")
        raise


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency untuk mendapatkan database session"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            await session.close()


async def close_database() -> None:
    """Menutup koneksi database"""
    try:
        await engine.dispose()
        logger.info("✅ Database connection closed")
    except Exception as e:
        logger.error(f"❌ Error closing database: {e}")


# Utility functions untuk database operations
class DatabaseManager:
    """Manager untuk operasi database umum"""
    
    @staticmethod
    async def execute_query(session: AsyncSession, query: str, params: dict = None):
        """Execute raw SQL query"""
        result = await session.execute(query, params or {})
        return result
    
    @staticmethod
    async def bulk_insert(session: AsyncSession, objects: list):
        """Bulk insert objects"""
        session.add_all(objects)
        await session.commit()
    
    @staticmethod
    async def get_table_stats(session: AsyncSession) -> dict:
        """Get statistics untuk semua tables"""
        from models.market_data import MarketData
        from models.signals import TradingSignal
        from models.portfolio import Portfolio, Position, Trade
        from models.news import NewsArticle
        
        stats = {}
        
        # Hitung jumlah records per table
        tables = {
            "market_data": MarketData,
            "signals": TradingSignal,
            "portfolios": Portfolio,
            "positions": Position,
            "trades": Trade,
            "news": NewsArticle
        }
        
        for table_name, model in tables.items():
            count = await session.query(model).count()
            stats[table_name] = count
            
        return stats