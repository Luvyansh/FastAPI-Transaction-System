# Transaction Ranking System

A practical full-stack project with FastAPI + SQLite backend and React frontend.
It supports transaction processing, per-user summary, and a fair leaderboard with basic abuse prevention.

## How To Run The Project

## Prerequisites

- Python 3.11+
- Node.js 18+

## 1) Backend

```bash
cd backend
py -3.11 -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend URL: `http://127.0.0.1:8000`  
Web URL: `http://127.0.0.1:8000/web` 
Swagger docs: `http://127.0.0.1:8000/docs`

## 2) Frontend

In a new terminal:

```bash
cd frontend
npm install
npm run dev
```

Frontend URL: `http://localhost:5173`  
Frontend calls backend via Vite proxy (`/api/*` -> `http://127.0.0.1:8000/*`).

## 2A) Frontend Template On Port 8000 (No Vite Server Needed)

The backend also serves a simple HTML client at:

- `http://127.0.0.1:8000/web`

This template calls the same API endpoints directly from the same origin, so no separate frontend dev server is required.

## 3) Optional: Generate Mock Data

From project root:

```bash
backend\venv\Scripts\python seed.py
```

`seed.py` clears existing data and inserts random users + random transactions.

## API Endpoints

## `POST /transaction`

Creates a transaction.

Request body:

```json
{
  "user_id": "alice",
  "amount": 25.5,
  "idempotency_key": "client-generated-unique-key"
}
```

Response behavior:
- `201`: new transaction saved
- `200`: duplicate retry (same idempotency key), existing transaction returned
- `409`: conflicting write race where existing row cannot be read after rollback
- `503`: database busy under contention, retry with same idempotency key
- `422`: validation failure

## `GET /summary/{user_id}`

Returns summary for one user:
- total amount of all transactions
- number of transactions
- average amount
- whether abuse rule is currently triggered

If user has no data, returns `404`.

## `GET /ranking`

Returns users sorted by ranking score (highest first) with:
- rank number
- user id
- score
- total amount
- number of transactions
- abuse flag

## Module-Level Breakdown

- `backend/app/main.py`: API routes, transaction orchestration, HTTP error mapping.
- `backend/app/schemas.py`: request/response validation models (Pydantic).
- `backend/app/models.py`: database tables (`transactions`, `user_stats`).
- `backend/app/database.py`: SQLAlchemy engine/session + SQLite settings (WAL mode, timeout).
- `backend/app/services.py`: business logic for idempotency checks, stats update, abuse check, and ranking score.
- `backend/app/static/index.html`: simple backend-served HTML template at `/web`.
- `seed.py`: local reseed script for mock/demo data generation.
- `frontend/src/api.js`: frontend API client.
- `frontend/src/components/*`: dashboard UI (submit transaction, summary lookup, leaderboard).

## Request Validation

Validation is handled by Pydantic in `TransactionCreate`:
- `user_id`: required, trimmed, non-empty, max length 64
- `idempotency_key`: required, trimmed, non-empty, max length 128
- `amount`: required, finite number, must be greater than 0 and less than or equal to 1,000,000

Invalid payloads return `422` with validation details.

## How Duplicate Requests Are Prevented

Three layers are used:

1. Client sends `idempotency_key` on every transaction request.
2. Service checks if that key already exists before insert.
3. Database enforces `UNIQUE` on `idempotency_key` as hard safety.

If duplicate is detected, existing transaction is returned (`200`) and user totals are not incremented again.

## How Simultaneous Requests Are Handled

- Write transaction starts with `BEGIN IMMEDIATE` to acquire SQLite write lock before read+write steps.
- SQLite engine has `timeout=15` seconds to reduce immediate lock failures during contention.
- If lock still cannot be acquired, API returns `503` with retry guidance.
- The same protection applies even if two requests arrive at the same moment from different clients (for example Vite UI and `/web` HTML template).
- If those concurrent requests use the same idempotency key, only one write is stored and the other receives the already-stored result (`200`, `duplicate: true`).

Important SQLite note: this is write-serialization, not true per-row lock behavior.

## How Consistent Data Updates Are Handled

`POST /transaction` updates are done in one database transaction:
- insert transaction row
- update user stats row (total amount, count, abuse fields)
- commit together

On any failure, rollback is executed so partial updates are not stored.

## Ranking Logic (Simple Explanation)

Ranking uses two factors:

1. Total amount of transactions
2. Number of transactions

Formula:

```text
Base score = (55 × ln(1 + Total amount)) + (45 × ln(1 + Number of transactions))
```

Abuse penalty:

```text
If user is flagged: Final score = Base score × 0.6
Else: Final score = Base score
```

Example:
- Total amount = 300
- Number of transactions = 10
- Base score = (55 × ln(301)) + (45 × ln(11))
- If flagged, final score = Base score × 0.6
- Then a tiny user-based decimal is added so two users do not end up with the exact same final score.

### Why this formula?

- `ln(1 + value)` is mathematically stable and reduces extreme outlier impact.
- It still rewards both high total amount and consistent transaction activity.
- It is harder to game than purely linear scoring at high values.
- The final tiny deterministic tie-break decimal makes scores unique without changing practical fairness.

### Why this scales to millions?

- Ranking reads from `user_stats` (one row per user), not from all transaction rows.
- Transaction writes keep `user_stats` up to date, so ranking does not recalculate from raw history.
- Time complexity is based on number of users in leaderboard, not number of historical transactions.

### Time complexity

- Calculating one user's score: `O(1)`
- Calculating scores for all users: `O(U)` where `U` is number of users
- Sorting all users by score: `O(U log U)`
- Total ranking endpoint complexity: `O(U log U)` (sorting dominates)

## Basic Abuse / Manipulation Prevention

Current abuse rule:
- If a user has 15 or more tiny transactions (amount < 1.00) within last 60 minutes, user is flagged.
- Flagged users get 40% penalty (`score × 0.6`).

Manipulation protection includes:
- positive and bounded amount validation
- finite-number validation (no `NaN`/infinite values)
- idempotency protection against duplicate replay inflation

## Edge Cases Handled

- Missing required fields -> `422`
- Empty `user_id` / `idempotency_key` after trimming -> `422`
- Zero or negative amount -> `422`
- Too large amount (> 1,000,000) -> `422`
- Non-finite amount -> `422`
- Same idempotency key replay -> `200` with `duplicate: true`
- User summary for unknown user -> `404`
- DB busy under concurrency -> `503` with retry message

## Mock Data And Assumptions

Mock/demo data:
- `seed.py` creates 25 users and around 450-500 random transactions (plus extra tiny bursts to demonstrate abuse flag).
- Running seed clears existing data and inserts fresh random data.

Assumptions:
- Single service instance, SQLite local file storage.
- Idempotency key is globally unique across all users.
- CORS is limited to local frontend addresses.
- Transport encryption (HTTPS) is expected at deployment layer (reverse proxy/platform), not implemented directly in app code.

## Mermaid Flowchart

```mermaid
flowchart TD
    A[User enters transaction in UI] --> B[Frontend sends POST request]
    B --> C{HTTPS/TLS enabled by deployment?}
    C -->|Yes| D[Request reaches backend]
    C -->|No (local dev)| D

    D --> E[Validate input fields]
    E -->|Invalid| F[Return 422 with error details]
    E -->|Valid| G[Start DB write transaction BEGIN IMMEDIATE]

    G --> H[Check idempotency key already exists?]
    H -->|Yes| I[Return existing transaction 200 duplicate true]
    H -->|No| J[Insert new transaction row]

    J --> K[Update user totals and counts]
    K --> L[Count tiny transactions in last 60 minutes]
    L --> M{Tiny count >= 15?}
    M -->|Yes| N[Mark user flagged]
    M -->|No| O[Keep user unflagged]

    N --> P[Commit all DB changes]
    O --> P
    P --> Q[Return 201 created]

    Q --> R[Leaderboard request]
    R --> S[Score = Total amount x 0.01 + Number of transactions x 2]
    S --> T{User flagged?}
    T -->|Yes| U[Final score = Score x 0.6]
    T -->|No| V[Final score = Score]
    U --> W[Sort users by final score]
    V --> W
    W --> X[Return ranking list]
```
