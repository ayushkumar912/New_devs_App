import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from ..config import settings

logger = logging.getLogger(__name__)


def to_async_database_url(url: str) -> str:
    """Rewrite a libpq URL so SQLAlchemy uses the asyncpg driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://"):]
    if url.startswith("postgresql://"):
        return "postgresql+asyncpg://" + url[len("postgresql://"):]
    raise ValueError("DATABASE_URL must be a postgresql URL")


class DatabasePool:
    def __init__(self):
        self.engine = None
        self.session_factory = None

    async def initialize(self):
        """Initialize database connection pool from DATABASE_URL."""
        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

        try:
            database_url = to_async_database_url(settings.database_url)

            # The async engine supplies its own pool. A sync QueuePool cannot be used here.
            self.engine = create_async_engine(
                database_url,
                pool_size=settings.database_pool_size,
                max_overflow=settings.database_max_overflow,
                pool_pre_ping=True,
                pool_recycle=settings.database_pool_recycle,
                echo=False,
            )

            self.session_factory = async_sessionmaker(
                bind=self.engine,
                class_=AsyncSession,
                expire_on_commit=False,
            )

            logger.info("Database connection pool initialized")

        except Exception as e:
            logger.error(f"Database pool initialization failed: {e}")
            if self.engine is not None:
                await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None

    @asynccontextmanager
    async def get_session(self):
        """Get database session from pool."""
        if not self.session_factory:
            raise RuntimeError("Database pool not initialized")
        session = self.session_factory()
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Global database pool instance
db_pool = DatabasePool()


async def get_db_session():
    """Dependency to get database session."""
    async with db_pool.get_session() as session:
        yield session
