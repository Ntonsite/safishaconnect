"""Admin: overview statistics, platform settings and audit history."""

from fastapi import APIRouter
from sqlalchemy import select

from app.api.v1.admin.common import PagingDep, admin_only, paginate
from app.models import AuditLog
from app.schemas.admin import AuditOut, SettingOut, SettingUpdate, StatsOut
from app.schemas.common import Page
from app.security.deps import AdminUser, DbSession
from app.services import admin_ops, audit, platform_settings

router = APIRouter(dependencies=admin_only)


@router.get("/stats", response_model=StatsOut, tags=["admin: overview"])
def stats(db: DbSession) -> StatsOut:
    return admin_ops.stats(db)


@router.get("/settings", response_model=list[SettingOut], tags=["admin: settings"])
def list_settings(db: DbSession) -> list[SettingOut]:
    return [SettingOut(**s) for s in platform_settings.list_settings(db)]


@router.put("/settings/{key}", response_model=list[SettingOut], tags=["admin: settings"])
def update_setting(key: str, data: SettingUpdate, db: DbSession, admin: AdminUser) -> list[SettingOut]:
    old, new = platform_settings.update_setting(db, key, data.value, admin.id)
    action = "ADMIN_CHANGED_COMMISSION" if key == "commission_percent" else "ADMIN_CHANGED_SETTING"
    audit.record(db, admin, action, "setting", key, {"from": old, "to": new})
    db.commit()
    return list_settings(db)


@router.get("/audit", response_model=Page[AuditOut], tags=["admin: audit"])
def audit_log(
    db: DbSession, paging: PagingDep, action: str | None = None, entity_type: str | None = None
) -> Page[AuditOut]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    rows, total = paginate(db, stmt, paging)
    items = [
        AuditOut(
            id=a.id,
            actor_name=a.actor.full_name if a.actor else None,
            action=a.action,
            entity_type=a.entity_type,
            entity_id=a.entity_id,
            details=a.details,
            created_at=a.created_at,
        )
        for a in rows
    ]
    return Page(items=items, total=total, page=paging.page, page_size=paging.page_size)
