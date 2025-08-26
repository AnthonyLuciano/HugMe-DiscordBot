from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, DateTime, Boolean
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class PixConfig(Base):
    __tablename__ = 'pix_config'

    id: Mapped[int] = mapped_column(primary_key=True)
    chave: Mapped[str] = mapped_column(String(100), nullable=False, unique=True)
    static_qr_url: Mapped[str | None] = mapped_column(String(255))
    nome_titular: Mapped[str] = mapped_column(String(100), nullable=False)
    cidade: Mapped[str] = mapped_column(String(100), nullable=False)
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    atualizado_por: Mapped[str | None] = mapped_column(String(20))

class Apoiador(Base):
    __tablename__ = 'apoiadores'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    discord_id: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    guild_id: Mapped[str] = mapped_column(String(20), nullable=False)
    id_pagamento: Mapped[str | None] = mapped_column(String(50), unique=True)
    tipo_apoio: Mapped[str] = mapped_column(String(20), nullable=False)
    duracao_meses: Mapped[int | None] = mapped_column(Integer)
    comprovante_url: Mapped[str | None] = mapped_column(String(255))
    data_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ultimo_pagamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    nivel: Mapped[int] = mapped_column(Integer, default=1)
    data_expiracao: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    cargo_atribuido: Mapped[bool] = mapped_column(Boolean, default=False)
    ja_pago: Mapped[bool] = mapped_column(Boolean, default=False)
    # Campos de pagamento restantes
    valor_doacao: Mapped[int | None] = mapped_column(Integer)  # Em centavos
    data_pagamento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metodo_pagamento: Mapped[str | None] = mapped_column(String(20))
    email_doador: Mapped[str | None] = mapped_column(String(100))


    def __repr__(self) -> str:
        return f"<Apoiador(discord_id={self.discord_id}, nivel={self.nivel})>"

class GuildConfig(Base):
    __tablename__ = 'guild_configs'
    
    guild_id: Mapped[str] = mapped_column(String(20), primary_key=True)
    role_prefix: Mapped[str] = mapped_column(String(50), default="Apoia")
    cargo_apoiador_id: Mapped[str | None] = mapped_column(String(20))  # New field for role ID
    webhook_failures: Mapped[int] = mapped_column(Integer, default=0)  # Failure counter
