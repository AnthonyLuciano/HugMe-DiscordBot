from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from bot.config import config
from sqlalchemy.exc import ArgumentError
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession


# Cria a conexão com o PostgreSQL
engine = create_engine(
    config.DATABASE_URL, # type: ignore
    pool_pre_ping=True,  # Verifica conexão antes de usar
    echo=False  # Altere para True para ver logs SQL (útil em desenvolvimento)
    
)

# Add async configuration
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    """Fornece uma sessão do banco de dados"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

