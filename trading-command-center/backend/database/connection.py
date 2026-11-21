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
        echo=False,
        connect_args={"check_same_thread": False}
    )
else:
    # Untuk database lain (PostgreSQL, MySQL, dll)
    engine = create_async_engine(
        DATABASE_URL,
        echo=False,
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
        if DATABASE_URL.startswith("sqlite:///"):  # folder file SQLite (mis. data/) belum tentu ada
            from pathlib import Path
            Path(DATABASE_URL[len("sqlite:///"):]).parent.mkdir(parents=True, exist_ok=True)
        async with engine.begin() as conn:
            # Import semua models
            from models.market_data import MarketData
            from models.signals import TradingSignal
            from models.portfolio import Position, Trade
            
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
