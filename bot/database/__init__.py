from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from starlette.config import Config as StarletteConfig
from bot.config import config


# Create async engine using DATABASE_URL (expects mysql+aiomysql://...)
DATABASE_URL = config.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Async session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


async def get_db():
    """Async DB session generator for FastAPI/async code."""
    async with AsyncSessionLocal() as session:
        yield session

