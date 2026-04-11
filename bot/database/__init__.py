from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from bot.config import config

DATABASE_URL = config.DATABASE_URL
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not configured")

engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    pool_pre_ping=True,      # evita conexões mortas
    pool_recycle=3600,       # recicla conexões a cada hora
)

AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session

async def close_db():
    """Fecha o engine antes do event loop encerrar."""
    await engine.dispose()