"""concurrency, idempotency and query-driven indexes

* optimistic ``version_id`` columns on bookings, payments and settlements
* booking ``Idempotency-Key`` support
* partial unique index: at most one open (offered/accepted) assignment per booking
* payment gateway callback ledger (``payment_gateway_events``) and payment reference uniqueness
* notification delivery outbox columns
* indexes derived from measured query patterns (docs/ARCHITECTURE_ASSESSMENT.md); redundant
  single-column indexes that are a prefix of a new composite index are dropped

Plain CREATE INDEX briefly blocks writes on the table. That is acceptable at pilot
volume; on very large tables prefer CREATE INDEX CONCURRENTLY in a maintenance window.

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02 13:13:55.959080
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0002'
down_revision: str | None = '0001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Repair data written by earlier versions so the new unique index can be built: keep the
    # accepted (else most recent) open assignment per booking and cancel the rest.
    op.execute(
        """
        UPDATE provider_assignments pa SET status = 'CANCELLED', responded_at = coalesce(responded_at, now()),
               response_note = 'Duplicate open assignment closed by migration 0002'
        FROM (
            SELECT id, row_number() OVER (
                PARTITION BY booking_id ORDER BY (status = 'ACCEPTED') DESC, offered_at DESC
            ) AS rn
            FROM provider_assignments WHERE status IN ('OFFERED', 'ACCEPTED')
        ) ranked
        WHERE pa.id = ranked.id AND ranked.rn > 1
        """
    )
    op.create_table('payment_gateway_events',
    sa.Column('gateway', sa.String(length=40), nullable=False),
    sa.Column('dedupe_key', sa.String(length=160), nullable=False),
    sa.Column('external_transaction_id', sa.String(length=120), nullable=False),
    sa.Column('status', sa.String(length=40), nullable=False),
    sa.Column('amount', sa.Numeric(precision=12, scale=2), nullable=True),
    sa.Column('currency', sa.String(length=3), nullable=True),
    sa.Column('payment_id', sa.Uuid(), nullable=True),
    sa.Column('outcome', sa.String(length=60), nullable=True),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.ForeignKeyConstraint(['payment_id'], ['payments.id'], name=op.f('fk_payment_gateway_events_payment_id_payments'), ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_payment_gateway_events'))
    )
    op.create_index(op.f('ix_payment_gateway_events_payment_id'), 'payment_gateway_events', ['payment_id'], unique=False)
    op.create_index('uq_payment_gateway_events_dedupe', 'payment_gateway_events', ['gateway', 'dedupe_key'], unique=True)
    op.add_column('bookings', sa.Column('version_id', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.add_column('bookings', sa.Column('idempotency_key', sa.String(length=64), nullable=True))
    op.add_column('bookings', sa.Column('idempotency_fingerprint', sa.String(length=64), nullable=True))
    op.drop_index('ix_bookings_customer_id', table_name='bookings')
    op.drop_index('ix_bookings_provider_id', table_name='bookings')
    op.drop_index('ix_bookings_status', table_name='bookings')
    op.create_index('ix_bookings_status_schedule', 'bookings', ['status', 'scheduled_date'], unique=False)
    op.create_unique_constraint('uq_bookings_customer_idempotency_key', 'bookings', ['customer_id', 'idempotency_key'])
    op.add_column('notifications', sa.Column('delivery_status', sa.String(length=16), nullable=True))
    op.add_column('notifications', sa.Column('delivery_attempts', sa.Integer(), server_default=sa.text('0'), nullable=False))
    op.add_column('notifications', sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('notifications', sa.Column('last_error', sa.String(length=255), nullable=True))
    op.create_index('ix_notifications_delivery_due', 'notifications', ['next_attempt_at'], unique=False, postgresql_where=sa.text("delivery_status = 'PENDING'"))
    op.create_index('ix_notifications_user_created', 'notifications', ['user_id', 'created_at'], unique=False)
    op.add_column('payments', sa.Column('version_id', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_index('ix_payments_created_at', 'payments', ['created_at'], unique=False)
    op.create_index('uq_payments_gateway_reference', 'payments', ['gateway', 'gateway_reference'], unique=True, postgresql_where=sa.text('gateway_reference IS NOT NULL'))
    op.drop_index('ix_provider_assignments_expires_at', table_name='provider_assignments')
    op.create_index('ix_assignments_open_offer_expiry', 'provider_assignments', ['expires_at'], unique=False, postgresql_where=sa.text("status = 'OFFERED'"))
    op.create_index('uq_assignments_one_open_per_booking', 'provider_assignments', ['booking_id'], unique=True, postgresql_where=sa.text("status IN ('OFFERED', 'ACCEPTED')"))
    op.add_column('provider_settlements', sa.Column('version_id', sa.Integer(), server_default=sa.text('1'), nullable=False))
    op.create_index('ix_provider_settlements_created_at', 'provider_settlements', ['created_at'], unique=False)
    op.create_index('ix_reviews_visible_recent', 'reviews', ['created_at'], unique=False, postgresql_where=sa.text('is_hidden = false'))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_reviews_visible_recent', table_name='reviews', postgresql_where=sa.text('is_hidden = false'))
    op.drop_index('ix_provider_settlements_created_at', table_name='provider_settlements')
    op.drop_column('provider_settlements', 'version_id')
    op.drop_index('uq_assignments_one_open_per_booking', table_name='provider_assignments', postgresql_where=sa.text("status IN ('OFFERED', 'ACCEPTED')"))
    op.drop_index('ix_assignments_open_offer_expiry', table_name='provider_assignments', postgresql_where=sa.text("status = 'OFFERED'"))
    op.create_index('ix_provider_assignments_expires_at', 'provider_assignments', ['expires_at'], unique=False)
    op.drop_index('uq_payments_gateway_reference', table_name='payments', postgresql_where=sa.text('gateway_reference IS NOT NULL'))
    op.drop_index('ix_payments_created_at', table_name='payments')
    op.drop_column('payments', 'version_id')
    op.drop_index('ix_notifications_user_created', table_name='notifications')
    op.drop_index('ix_notifications_delivery_due', table_name='notifications', postgresql_where=sa.text("delivery_status = 'PENDING'"))
    op.drop_column('notifications', 'last_error')
    op.drop_column('notifications', 'next_attempt_at')
    op.drop_column('notifications', 'delivery_attempts')
    op.drop_column('notifications', 'delivery_status')
    op.drop_constraint('uq_bookings_customer_idempotency_key', 'bookings', type_='unique')
    op.drop_index('ix_bookings_status_schedule', table_name='bookings')
    op.create_index('ix_bookings_status', 'bookings', ['status'], unique=False)
    op.create_index('ix_bookings_provider_id', 'bookings', ['provider_id'], unique=False)
    op.create_index('ix_bookings_customer_id', 'bookings', ['customer_id'], unique=False)
    op.drop_column('bookings', 'idempotency_fingerprint')
    op.drop_column('bookings', 'idempotency_key')
    op.drop_column('bookings', 'version_id')
    op.drop_index('uq_payment_gateway_events_dedupe', table_name='payment_gateway_events')
    op.drop_index(op.f('ix_payment_gateway_events_payment_id'), table_name='payment_gateway_events')
    op.drop_table('payment_gateway_events')
    # ### end Alembic commands ###
