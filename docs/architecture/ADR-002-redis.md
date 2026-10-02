# ADR-002: Redis is deferred

- **Status:** Deferred, with explicit triggers below.
- **Date:** 2 October 2026

## Context

The question was whether SafishaCon needs Redis for caching, rate limiting, distributed locks, sessions or revocation, a job broker, or assignment coordination. I measured before deciding:

| Question | Evidence | Answer |
|---|---|---|
| Is PostgreSQL the bottleneck? | Under saturating load, PostgreSQL CPU was about 4%. The slow endpoints were slow because of N+1 queries, unbounded results and Python CPU. All of that is now fixed, and p50 fell from 1,100 ms to 48 ms with no cache. | **No** |
| Is repeated computation expensive? | The catalog, areas and config queries take under 1 ms. Availability now uses 6 queries. Admin stats is one 44 ms aggregate, run only on an admin page load. | **No** |
| Do multiple replicas need shared ephemeral state? | One API container (2 processes) handles the pilot with more than 40× headroom. JWT authentication is stateless. Refresh tokens and revocation live in PostgreSQL. The only per-process state is the rate limiter. | **Not yet** |
| Would caching be safe? | Pricing must be read live (commission changes apply immediately), and assignment needs strong consistency. Settings are cached only **per request**. | Only for the public catalog, at most |
| Is it needed as a job broker? | Jobs are claimed from PostgreSQL with `FOR UPDATE SKIP LOCKED` ([ADR-005](ADR-005-background-jobs.md)). | **No** |

## Decision

**Do not add Redis now.** Instead:

- **Rate limiting:** an in-process sliding window per API process. Memory is bounded: idle buckets are swept.
- **Edge rate limiting:** nginx `limit_req` on the credential endpoints, which is shared across all API replicas behind that nginx.
- **Distributed coordination:** PostgreSQL row locks and `SKIP LOCKED` ([ADR-001](ADR-001-database.md)).

## Trade-off accepted

With N API processes, the in-process login limit is N × 20 attempts per minute per IP. The nginx edge limit is the shared ceiling. That is acceptable for a pilot with 2 processes.

## Adopt Redis when any of these hold

1. More than one API **container** serves production traffic **and** per-account or per-IP limits must be exact. Then move `SlidingWindowLimiter` to Redis (`INCR` + `EXPIRE`).
2. Public catalog or config endpoints exceed about 30% of API CPU at peak, or you need an HTTP response cache.
   - **Cache only:** `catalog:services:v{n}`, `catalog:areas:v{n}`, `config:public:v{n}`.
   - **TTL:** 60 s.
   - **Invalidate:** bump `{n}` on admin catalog edits.
   - **If Redis is down:** fall through to PostgreSQL.
3. You need real-time fan-out (provider app live updates over WebSockets/SSE) across replicas: Redis pub/sub.

## Never

- Cache prices or commission as the authoritative value. Quotes and bookings always read PostgreSQL.
- Cache booking, assignment or payment state used for decisions.
- Hold assignment locks in Redis instead of PostgreSQL.
- Let a Redis outage fail a booking. Every Redis use must degrade to PostgreSQL or to "no limit".
