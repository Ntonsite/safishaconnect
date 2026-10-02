from typing import Annotated, Any

from fastapi import Depends, Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.enums import RoleCode
from app.security.deps import require_roles

admin_only = [Depends(require_roles(RoleCode.ADMIN))]


class Paging:
    def __init__(
        self,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=100)] = 25,
    ) -> None:
        self.page, self.page_size = page, page_size


PagingDep = Annotated[Paging, Depends()]


def paginate(db: Session, stmt: Select, paging: Paging) -> tuple[list[Any], int]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = db.scalars(stmt.offset((paging.page - 1) * paging.page_size).limit(paging.page_size)).unique().all()
    return list(rows), total
