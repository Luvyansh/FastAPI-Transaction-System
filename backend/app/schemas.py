from datetime import datetime
import math

from pydantic import BaseModel, Field, field_validator

MAX_TRANSACTION_AMOUNT = 1_000_000.0


class TransactionCreate(BaseModel):
    user_id: str = Field(..., min_length=1, max_length=64)
    amount: float = Field(
        ...,
        gt=0,
        le=MAX_TRANSACTION_AMOUNT,
        description="Transaction amount must be positive and reasonably bounded",
    )
    idempotency_key: str = Field(..., min_length=1, max_length=128)

    @field_validator("user_id", "idempotency_key")
    @classmethod
    def strip_whitespace(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must not be empty")
        return stripped

    @field_validator("amount")
    @classmethod
    def ensure_finite_amount(cls, value: float) -> float:
        if not math.isfinite(value):
            raise ValueError("amount must be a finite number")
        return value


class TransactionResponse(BaseModel):
    id: int
    user_id: str
    amount: float
    idempotency_key: str
    created_at: datetime
    duplicate: bool = False

    model_config = {"from_attributes": True}


class UserSummary(BaseModel):
    user_id: str
    total_volume: float
    transaction_count: int
    average_amount: float
    abuse_flagged: bool


class RankingEntry(BaseModel):
    rank: int
    user_id: str
    score: float
    total_volume: float
    transaction_count: int
    abuse_flagged: bool


class RankingResponse(BaseModel):
    rankings: list[RankingEntry]
