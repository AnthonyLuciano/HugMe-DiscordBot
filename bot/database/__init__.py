from sqlalchemy import create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from bot.config import config

# Configuração do banco de dados assíncrono
async_engine = create_async_engine(
    config.DATABASE_URL,
    echo=False,  # Set to True for SQL query logging
    pool_pre_ping=True,
)

# Factory para criar sessões assíncronas
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# Configuração do banco de dados síncrono (para FastAPI)
engine = create_engine(
    config.DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# Factory para criar sessões síncronas
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)

# Base declarativa para modelos
class Base(DeclarativeBase):
    pass

def get_db():
    """Fornece uma sessão síncrona do banco de dados para FastAPI"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()