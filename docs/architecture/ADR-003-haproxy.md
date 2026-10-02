# ADR-003: HAProxy is deferred; nginx (or the cloud load balancer) is the edge

- **Status:** Deferred.
- **Date:** 2 October 2026

## Context

| Question | Answer today |
|---|---|
| Are multiple FastAPI instances deployed? | One API container. Inside it, uvicorn runs `WEB_CONCURRENCY=2` worker processes, and the kernel balances connections between them. |
| Is load balancing required? | No. One 2-vCPU container sustains about 40 req/s against a pilot peak of under 1 req/s. |
| Where is TLS terminated? | At the platform edge (cloud load balancer or managed ingress), or at nginx with a certificate. |
| Is a reverse proxy already present? | Yes. nginx serves the SPA and proxies `/api` to the API. It also does gzip, caching headers, the edge auth rate limit, request IDs, timeouts and the trusted `X-Forwarded-For`. |
| Would HAProxy add health checking or routing value? | Not with one backend. Docker health checks (`/health/ready`) and the orchestrator already gate traffic. |

## Decision

**Do not add HAProxy.** nginx remains the single reverse proxy. The API is kept **stateless**, so scaling out needs no code changes:

- authentication uses bearer tokens with no server sessions;
- jobs run in a separate worker and coordinate through PostgreSQL;
- idempotency and locks live in the database;
- migrations take an advisory lock.

## Scaling path (no rewrite)

1. **More capacity, same box:** raise the container's CPUs and `WEB_CONCURRENCY` (1 process per vCPU), keeping `pool × processes` within the connection budget ([ADR-001](ADR-001-database.md)).
2. **Several API containers:** use the platform's load balancer if there is one (cloud LB, Kubernetes Service, Fly or Render routing). Without one, add an `upstream` block of API replicas to the existing nginx, with `max_fails`/`fail_timeout` passive checks, or introduce HAProxy at that point if active health checks, connection draining or per-backend stats are needed.
3. **When adding a balancer in front of nginx:** set `real_ip_header`/`set_real_ip_from` for that balancer only, and add its address to `FORWARDED_ALLOW_IPS`.

## Revisit when

- Two or more API containers must run on hosts **without** a managed load balancer, and nginx's passive health checking proves insufficient.
- Blue/green or canary deploys need weighted routing.
