import os
import random
import sys
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4


ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
os.chdir(BACKEND_DIR)
sys.path.insert(0, str(BACKEND_DIR))

from app.database import SessionLocal, Base, engine  # noqa: E402
from app.models import Transaction, UserStats  # noqa: E402


USER_COUNT = 25
MIN_TRANSACTIONS = 450
MAX_TRANSACTIONS = 500

MICRO_TX_THRESHOLD = 1.0
ABUSE_MICRO_TX_LIMIT = 15


def random_user_ids() -> list[str]:
    return [f"user_{index:02d}" for index in range(1, USER_COUNT + 1)]


def weighted_amount() -> float:
    """
    Keep amounts realistic:
    - most are normal transactions
    - some are tiny transactions to exercise abuse logic
    """
    if random.random() < 0.12:
        return round(random.uniform(0.1, 0.99), 2)
    return round(random.uniform(5, 400), 2)


def random_timestamp() -> datetime:
    now = datetime.utcnow()
    minutes_ago = random.randint(0, 30 * 24 * 60)
    return now - timedelta(minutes=minutes_ago)


def build_transactions() -> list[Transaction]:
    users = random_user_ids()
    total_tx = random.randint(MIN_TRANSACTIONS, MAX_TRANSACTIONS)
    transactions: list[Transaction] = []

    for _ in range(total_tx):
        user_id = random.choice(users)
        transactions.append(
            Transaction(
                user_id=user_id,
                amount=weighted_amount(),
                idempotency_key=str(uuid4()),
                created_at=random_timestamp(),
            )
        )

    # Add a small burst of micro-transactions for random users so ranking
    # penalty behavior can be observed in seeded data.
    burst_users = random.sample(users, k=3)
    now = datetime.utcnow()
    for user_id in burst_users:
        for _ in range(ABUSE_MICRO_TX_LIMIT + random.randint(0, 5)):
            transactions.append(
                Transaction(
                    user_id=user_id,
                    amount=round(random.uniform(0.1, 0.95), 2),
                    idempotency_key=str(uuid4()),
                    created_at=now - timedelta(minutes=random.randint(0, 59)),
                )
            )

    return transactions


def build_user_stats(transactions: list[Transaction]) -> list[UserStats]:
    by_user: dict[str, list[Transaction]] = {}
    for tx in transactions:
        by_user.setdefault(tx.user_id, []).append(tx)

    cutoff = datetime.utcnow() - timedelta(minutes=60)
    stats_rows: list[UserStats] = []

    for user_id, txs in by_user.items():
        total_volume = round(sum(tx.amount for tx in txs), 2)
        transaction_count = len(txs)
        micro_count_1h = sum(
            1
            for tx in txs
            if tx.amount < MICRO_TX_THRESHOLD and tx.created_at >= cutoff
        )
        abuse_flagged = micro_count_1h >= ABUSE_MICRO_TX_LIMIT

        stats_rows.append(
            UserStats(
                user_id=user_id,
                total_volume=total_volume,
                transaction_count=transaction_count,
                micro_tx_count_1h=micro_count_1h,
                abuse_flagged=abuse_flagged,
                updated_at=datetime.utcnow(),
            )
        )

    return stats_rows


def reseed() -> None:
    Base.metadata.create_all(bind=engine)
    session = SessionLocal()
    try:
        # Delete child table first for FK safety if schema evolves.
        session.query(Transaction).delete()
        session.query(UserStats).delete()

        transactions = build_transactions()
        stats_rows = build_user_stats(transactions)

        session.add_all(transactions)
        session.add_all(stats_rows)
        session.commit()

        print("Seed complete")
        print(f"Users: {len(stats_rows)}")
        print(f"Transactions: {len(transactions)}")
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    reseed()
