from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

# Base class for SQLAlchemy models
Base = declarative_base()

class Supporter(Base):
    __tablename__ = 'supporters'

    id = Column(Integer, primary_key=True, autoincrement=True)
    discord_id = Column(String, unique=True, nullable=False)
    donation_status = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)

    # Relationship to link supporters with their donations
    donations = relationship("Donation", back_populates="supporter")

class Donation(Base):
    __tablename__ = 'donations'

    id = Column(Integer, primary_key=True, autoincrement=True)
    supporter_id = Column(Integer, ForeignKey('supporters.id'), nullable=False)
    amount = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)

    # Relationship to link donations with their supporter
    supporter = relationship("Supporter", back_populates="donations")