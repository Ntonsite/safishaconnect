"""Engine, session factory and the request-scoped session dependency.

The API is deliberately synchronous (psycopg 3 + SQLAlchemy ORM): FastAPI runs
``def`` endpoints in a thread pool, so blocking database calls never stall the
event loop. See docs/architecture/ADR-001-database.md.
"""

from collections.abc import Iterator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core import context
from app.core.config import get_settings

_s = get_settings()

engine = create_engine(
    _s.database_url,
    pool_size=_s.db_pool_size,
    max_overflow=_s.db_max_overflow,
    pool_timeout=_s.db_pool_timeout_seconds,
    pool_recycle=_s.db_pool_recycle_seconds,
    pool_pre_ping=True,
    connect_args={
        "connect_timeout": _s.db_connect_timeout_seconds,
        "application_name": f"{_s.app_name.lower()}-api",
        # Server-side guards: a slow query or a stuck lock fails one request instead of
        # silently exhausting the pool for everyone.
        "options": (
            f"-c statement_timeout={_s.db_statement_timeout_ms}"
            f" -c lock_timeout={_s.db_lock_timeout_ms}"
            f" -c idle_in_transaction_session_timeout={_s.db_idle_in_transaction_timeout_ms}"
        ),
    },
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@event.listens_for(engine, "before_cursor_execute")
def _count_queries(*_args, **_kwargs) -> None:
    context.count_query()


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
