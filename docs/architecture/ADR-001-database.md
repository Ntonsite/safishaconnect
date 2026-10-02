# ADR-001: PostgreSQL as the single source of truth, with synchronous SQLAlchemy and row-level locking

- **Status:** Adopted. Re-confirmed 2 October 2026 by the architecture audit.
- **Deciders:** engineering

## Context

SafishaCon's core value is correctness: one cleaner per booking, never double-booked; one payment and one settlement per booking; prices frozen at booking time. The workload is small and transactional (bookings, offers, payments) with modest reporting. The audit showed PostgreSQL at about 4% CPU even while the API container was saturated. The application, not the database, was the bottleneck.

## Decision

1. **PostgreSQL is the authoritative store for all business state:**
   - bookings, price snapshots, assignments, payments, settlements, reviews and audit;
   - background-job state (offer expiry, notification outbox);
   - the payment-callback ledger.

   No cache or queue is ever authoritative for money or assignments.
2. **Synchronous SQLAlchemy 2 + psycopg 3, synchronous `def` endpoints.**
   - FastAPI runs them in a thread pool, so blocking DB I/O never blocks the event loop.
   - There are no `async def` endpoints, and none calls blocking code.
   - We deliberately do **not** mix async and sync database access.
3. **Concurrency control is in the database:**
   - **Pessimistic row locks** (`SELECT … FOR NO KEY UPDATE`) on the booking row for every state change. The provider row is also locked before capacity is consumed. Lock order is always booking → provider. The dispatcher and the worker use `SKIP LOCKED`, so they never wait on user requests.
   - **Optimistic version columns** (`version_id`) on bookings, payments and settlements. Any write based on stale data fails with a 409 instead of overwriting.
   - **Constraints as the last line of defence:**
     - a partial unique index for one open assignment per booking;
     - unique `(customer_id, idempotency_key)`;
     - unique gateway references and callback dedupe keys;
     - unique settlement and review per booking;
     - CHECK `commission + earning = total`.
4. **Bounded waiting.** `lock_timeout` (5 s), `statement_timeout` (15 s), `idle_in_transaction_session_timeout` (30 s), a connect timeout and a pool timeout are all configured by environment variable. Contention and overload surface as 409 or 503 with `Retry-After`, not as hangs.
5. **Connection pool:** per process `pool_size=5`, `max_overflow=5`, `pool_pre_ping`, `pool_recycle=1800`.

   Total connections = API containers × `WEB_CONCURRENCY` × 10 + worker (2) + admin headroom. The pilot is 1 × 2 × 10 + 2 = 22 of PostgreSQL's 100.

## Alternatives considered

| Alternative | Why not |
|---|---|
| Async SQLAlchemy (asyncpg) | Rewrites every service for no measured gain. The bottleneck was query count and Python CPU, not waiting on I/O. A half-async codebase is the worst outcome. |
| `SERIALIZABLE` isolation everywhere | Correct, but every conflict becomes a retry loop around whole requests. Explicit locks on the two contended rows (booking, provider) are simpler to reason about and test. |
| Application-level distributed locks (Redis) | Adds a second system whose failure modes interact with PostgreSQL's. Row locks are transactional and released automatically on crash. |
| Optimistic locking only | Fine for rare conflicts, but accept, expiry and cancel collide on the *same* booking by design. Locks give deterministic winners and clear error codes. |

## Consequences

- **Benefits:**
  - One system to back up, monitor and reason about.
  - Locks vanish on crash or restart.
  - The 9 concurrency tests pass deterministically.
- **Costs:**
  - Lock waits are possible under heavy contention on the same booking (bounded by `lock_timeout`).
  - Write throughput is bounded by one primary, far above SafishaCon's needs for the foreseeable future.

## Revisit when

- PostgreSQL CPU stays above 60%, or p95 query time grows despite indexes. First add a **read replica** for reporting and admin, then consider partitioning `bookings` and `booking_status_history` by month.
- Bookings pass about 10M, or multiple cities need isolation.
- Lock-timeout 409s exceed 0.1% of booking mutations.
