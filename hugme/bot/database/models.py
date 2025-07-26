from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone

Base = declarative_base()

class PixConfig(Base):
    __tablename__ = 'pix_config'

    id = Column(Integer, primary_key=True)
    chave = Column(String(100), nullable=False, unique=True)
    static_qr_url = Column(String(255))
    nome_titular = Column(String(100), nullable=False)
    cidade = Column(String(100), nullable=False)
    atualizado_em = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    atualizado_por = Column(String(20))

class Apoiador(Base):
    __tablename__ = 'apoiadores'
    
    id = Column(Integer, primary_key=True)
    discord_id = Column(String(20), unique=True, nullable=False)  # ID do usuário no Discord
    id_pagamento = Column(String(50), unique=True)  # ID único do pagamento (pode ser usado para outros gateways)
    tipo_apoio = Column(String(20), nullable = False) #pix ou paypal
    comprovante_url = Column(String(255)) #URL do Comprovante
    data_inicio = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))  # Data de início do apoio
    ultimo_pagamento = Column(DateTime(timezone=True))  # Data do último pagamento
    ativo = Column(Boolean, default=True)  # Status do apoio (ativo/inativo)
    nivel = Column(Integer, default=1)  # Nível de apoio (1 a 10, por exemplo)
    data_expiracao = Column(DateTime(timezone=True))  # Data de expiração dos benefícios

    def __repr__(self):
        return f"<Apoiador(discord_id={self.discord_id}, nivel={self.nivel})>"