from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import Transaction
from app.schemas import (
    RankingEntry,
    RankingResponse,
    TransactionCreate,
    TransactionResponse,
    UserSummary,
)
from app.services import get_rankings, get_user_summary, process_transaction

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Transaction Ranking API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static HTML client served from the backend itself on port 8000.
STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/web", StaticFiles(directory=STATIC_DIR, html=True), name="web")


@app.post("/transaction", response_model=TransactionResponse)
def create_transaction(payload: TransactionCreate, db: Session = Depends(get_db)):
    try:
        db.execute(text("BEGIN IMMEDIATE"))
        tx, is_duplicate = process_transaction(
            db,
            user_id=payload.user_id,
            amount=payload.amount,
            idempotency_key=payload.idempotency_key,
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(
            select(Transaction).where(Transaction.idempotency_key == payload.idempotency_key)
        )
        if existing:
            body = TransactionResponse.model_validate(existing).model_copy(
                update={"duplicate": True}
            ).model_dump(mode="json")
            return JSONResponse(status_code=200, content=body)
        raise HTTPException(status_code=409, detail="Transaction conflict")
    except OperationalError:
        db.rollback()
        raise HTTPException(
            status_code=503,
            detail="Database is busy, please retry with the same idempotency_key",
        )
    except Exception:
        db.rollback()
        raise

    body = TransactionResponse.model_validate(tx).model_copy(
        update={"duplicate": is_duplicate}
    ).model_dump(mode="json")
    status_code = 200 if is_duplicate else 201
    return JSONResponse(status_code=status_code, content=body)


@app.get("/summary/{user_id}", response_model=UserSummary)
def user_summary(user_id: str, db: Session = Depends(get_db)):
    stats = get_user_summary(db, user_id)
    if stats is None:
        raise HTTPException(
            status_code=404, detail=f"No transactions found for user '{user_id}'"
        )

    average = (
        stats.total_volume / stats.transaction_count if stats.transaction_count else 0.0
    )
    return UserSummary(
        user_id=stats.user_id,
        total_volume=round(stats.total_volume, 2),
        transaction_count=stats.transaction_count,
        average_amount=round(average, 2),
        abuse_flagged=stats.abuse_flagged,
    )


@app.get("/ranking", response_model=RankingResponse)
def ranking(db: Session = Depends(get_db)):
    entries = get_rankings(db)
    return RankingResponse(rankings=[RankingEntry(**entry) for entry in entries])
