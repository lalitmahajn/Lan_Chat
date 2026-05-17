"""SQLAlchemy async database setup."""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase

from server.config import get_db_path


class Base(DeclarativeBase):
    pass


# Engine + session factory — initialized on server startup
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        db_path = get_db_path()
        _engine = create_async_engine(
            f"sqlite+aiosqlite:///{db_path}",
            echo=False,
        )
    return _engine


def get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _session_factory


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields async DB session."""
    factory = get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def create_tables():
    """Create all tables. Called on server startup."""
    from server.models import Base as _  # noqa: ensure models registered
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def shutdown_db():
    """Close engine on server shutdown."""
    global _engine, _session_factory
    if _engine:
        await _engine.dispose()
        _engine = None
        _session_factory = None
