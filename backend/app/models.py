from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    # Unique constraint is the last line of defense against duplicate processing.
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        Index("ix_transactions_user_created", "user_id", "created_at"),
    )


class UserStats(Base):
    """Denormalized counters so summary/ranking queries stay fast."""

    __tablename__ = "user_stats"

    user_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    total_volume: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    transaction_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    micro_tx_count_1h: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    abuse_flagged: Mapped[bool] = mapped_column(default=False, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
