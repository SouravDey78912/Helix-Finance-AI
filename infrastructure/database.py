"""
infrastructure/database.py
===========================
PostgreSQL async database client using SQLAlchemy 2.0 async.

Local:       PostgreSQL in Docker Compose (free)
Production:  HA PostgreSQL (RDS, Azure Database, Cloud SQL)

Migration path: Change DATABASE_URL env var only — no code changes.

TODO: Define SQLAlchemy ORM models (User, Document, AuditLog, etc.)
TODO: Create Alembic migration scripts.
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from apps.config import get_settings

settings = get_settings()

# ── Engine ────────────────────────────────────────────────────────────────────
# TODO: Enable connection pooling settings for production
engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,  # verify connections before use
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""
    pass


async def get_session() -> AsyncSession:
    """
    Async context manager yielding a database session.

    Usage:
        async with get_session() as session:
            result = await session.execute(...)

    TODO: Add session-level audit logging.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """
    Create all tables on startup (development only).

    TODO: In production, use Alembic migrations instead.
    """
    # Import models here to register them on Base.metadata before creation
    from apps.models.user import User  # noqa: F401
    from apps.models.document import Document  # noqa: F401
    from security.password import hash_password

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Seed default user for testing
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "admin@helix.ai"))
        existing_user = result.scalar_one_or_none()
        if not existing_user:
            admin_user = User(
                email="admin@helix.ai",
                hashed_password=hash_password("admin123"),
                first_name="Admin",
                last_name="User",
                is_active=True,
                roles=["admin", "user"]
            )
            session.add(admin_user)
            await session.commit()

