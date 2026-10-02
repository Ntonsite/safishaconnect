# ADR-004: Kafka is deferred; in-process domain events are delivered after commit

- **Status:** Kafka deferred. Domain-event abstraction adopted.
- **Date:** 2 October 2026

## Context

These business events could eventually feed several consumers:

- `booking.created`
- `provider.assignment.requested`
- `provider.assigned`
- `booking.status_changed` (en route, started, completed…)
- `payment.completed`
- `settlement.settled`

Possible consumers include notifications, analytics, audit, a CRM, fraud and risk checks, and reporting.

### What Kafka would solve

Kafka provides **durable, replayable, high-throughput event streams consumed independently by many services**. It is the right tool when several teams or services must each process every event at their own pace, replay history to rebuild state, or absorb tens of thousands of events per second.

### Does SafishaCon have that problem now?

| Question | Today |
|---|---|
| Multiple independent consumers? | No. Notifications are written in the same transaction, and audit is a table. There is no CRM, data warehouse or fraud service. |
| High-throughput streaming? | No. The pilot is roughly hundreds of events a day; even Stage B is far below 100 events per second. |
| Need to replay events? | No. PostgreSQL holds the full booking, status and payment history (the status history alone has 1.3M rows in the test data). |
| Is the operational cost justified? | No. A Kafka cluster (or a managed one) means brokers, schema governance, consumer-lag monitoring and on-call knowledge for a team of a few engineers. |

## Decision

1. **Don't add Kafka.**
2. **Establish the seam now.** `app/core/events.py` holds the event plumbing:
   - Services call `events.publish(db, events.BOOKING_CREATED, …)`.
   - Events are parked on the database session and dispatched **only after `COMMIT`**. A rollback discards them.
   - A failing subscriber is logged and never affects the business operation.
   - Today's subscribers are structured logs (`domain_event`) and Prometheus business metrics.
3. **Event names are dotted, past-tense, stable strings.** They are ready to become topic names or routing keys.

## The path when the need appears

1. **Durable delivery to one or two external consumers** (for example a CRM or an analytics warehouse): add an `event_outbox` table written **in the same transaction** as the business change (subscribe at publish time, not after commit). A worker relays it, with the same `SKIP LOCKED` pattern as the notification outbox ([ADR-005](ADR-005-background-jobs.md)). This gives at-least-once delivery with no new infrastructure.
2. **Kafka (or a managed equivalent such as Redpanda, Confluent or MSK)** only when all three hold:
   - at least 3 independent consuming services or teams;
   - a need to replay history into new consumers;
   - sustained throughput the outbox relay cannot keep up with (more than about 1,000 events/s), or cross-region fan-out.

   The outbox relay then publishes to Kafka. No business code changes.

## Consequences

- **Today:**
  - Zero new infrastructure.
  - Notifications, metrics and logging are already decoupled from the booking, assignment and payment code.
  - Events are lost if the process dies *between* commit and dispatch. That is acceptable, because current subscribers are logs and metrics, never business state.
- **Later:** moving to an outbox, then Kafka, is additive.
