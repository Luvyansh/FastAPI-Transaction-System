from datetime import datetime, timedelta
import hashlib
import math

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Transaction, UserStats

# Micro-transaction threshold and abuse window
MICRO_TX_THRESHOLD = 1.0
ABUSE_WINDOW_MINUTES = 60
ABUSE_MICRO_TX_LIMIT = 15

# Ranking weights for log-scaled scoring.
VOLUME_WEIGHT = 55.0
FREQUENCY_WEIGHT = 45.0
ABUSE_PENALTY_FACTOR = 0.6
# Very small deterministic component to avoid equal final scores.
UNIQUE_EPSILON = 1e-6


def count_recent_micro_transactions(db: Session, user_id: str) -> int:
    cutoff = datetime.utcnow() - timedelta(minutes=ABUSE_WINDOW_MINUTES)
    return (
        db.scalar(
            select(func.count())
            .select_from(Transaction)
            .where(
                Transaction.user_id == user_id,
                Transaction.amount < MICRO_TX_THRESHOLD,
                Transaction.created_at >= cutoff,
            )
        )
        or 0
    )


def calculate_score(total_volume: float, transaction_count: int, abuse_flagged: bool) -> float:
    # Log scaling prevents extremely large spenders from dominating forever,
    # while still rewarding both amount and repeated activity.
    amount_component = VOLUME_WEIGHT * math.log1p(total_volume)
    frequency_component = FREQUENCY_WEIGHT * math.log1p(transaction_count)
    base_score = amount_component + frequency_component

    if abuse_flagged:
        base_score *= ABUSE_PENALTY_FACTOR

    return base_score


def unique_tiebreaker(user_id: str) -> float:
    # Use first 48 bits of SHA-256 as a stable fractional tie-breaker.
    # This keeps ordering deterministic across servers and requests.
    digest_prefix = hashlib.sha256(user_id.encode("utf-8")).hexdigest()[:12] #Hash Function -> Deterministic output
    normalized = int(digest_prefix, 16) / float(16**12)
    return normalized * UNIQUE_EPSILON


def get_or_create_user_stats(db: Session, user_id: str) -> UserStats:
    stats = db.scalar(
        select(UserStats).where(UserStats.user_id == user_id).with_for_update()
    )
    if stats is None:
        stats = UserStats(user_id=user_id)
        db.add(stats)
        db.flush()
        stats = db.scalar(
            select(UserStats).where(UserStats.user_id == user_id).with_for_update()
        )
    return stats


def process_transaction(
    db: Session,
    user_id: str,
    amount: float,
    idempotency_key: str,
) -> tuple[Transaction, bool]:
    """
    Process a transaction inside a caller-managed DB transaction.

    Returns (transaction, is_duplicate). On duplicate idempotency_key we return
    the existing row without mutating stats - safe for concurrent retries.
    """
    existing = db.scalar(
        select(Transaction).where(Transaction.idempotency_key == idempotency_key)
    )
    if existing:
        return existing, True

    # BEGIN IMMEDIATE is issued by the route before calling this function.
    # Lock the user's stats row so parallel requests for the same user serialize.
    stats = get_or_create_user_stats(db, user_id)

    tx = Transaction(
        user_id=user_id,
        amount=amount,
        idempotency_key=idempotency_key,
    )
    db.add(tx)
    db.flush()

    stats.total_volume += amount
    stats.transaction_count += 1
    stats.updated_at = datetime.utcnow()

    micro_count = count_recent_micro_transactions(db, user_id)
    stats.micro_tx_count_1h = micro_count
    stats.abuse_flagged = micro_count >= ABUSE_MICRO_TX_LIMIT

    return tx, False


def get_user_summary(db: Session, user_id: str) -> UserStats | None:
    return db.get(UserStats, user_id)


def get_rankings(db: Session) -> list[dict]:
    stats_rows = db.scalars(select(UserStats)).all()
    entries = []
    for stats in stats_rows:
        base_score = calculate_score(
            stats.total_volume,
            stats.transaction_count,
            stats.abuse_flagged,
        )
        final_score = round(base_score + unique_tiebreaker(stats.user_id), 6)
        entries.append(
            {
                "user_id": stats.user_id,
                "score": final_score,
                "total_volume": stats.total_volume,
                "transaction_count": stats.transaction_count,
                "abuse_flagged": stats.abuse_flagged,
            }
        )

    entries.sort(key=lambda entry: entry["score"], reverse=True)
    for index, entry in enumerate(entries, start=1):
        entry["rank"] = index
    return entries
