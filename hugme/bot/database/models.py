from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class Supporter(Base):
    __tablename__ = 'supporters'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)
    pagbank_id = Column(String(50), unique=True)
    supporter_since = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_payment = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    tier = Column(Integer, default=1)
    benefits_expire = Column(DateTime(timezone=True))
    
    def __repr__(self):
        return f"<Supporter(discord_id={self.discord_id}, tier={self.tier})>"
