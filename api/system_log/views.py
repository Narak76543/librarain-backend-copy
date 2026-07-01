from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from core.db import get_db
from api.system_log.models import TBL_SYSTEM_LOG
from api.auth_user.views import require_admin
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.views import response

router = APIRouter()

# GET /api/v1/admin/logs
@router.get("/api/v1/admin/logs", tags=["System Logs"])
def get_system_logs(
    module    : str | None = Query(None),
    action    : str | None = Query(None),
    level     : str | None = Query(None),
    status    : str | None = Query(None),
    user_email: str | None = Query(None),
    date_from : str | None = Query(None),
    date_to   : str | None = Query(None),
    search    : str | None = Query(None),
    limit     : int        = Query(50,  ge=1, le=500),
    offset    : int        = Query(0,   ge=0),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db        : Session         = Depends(get_db),
):
    query = db.query(TBL_SYSTEM_LOG)

    if module:     query = query.filter(TBL_SYSTEM_LOG.module     == module.upper())
    if action:     query = query.filter(TBL_SYSTEM_LOG.action     == action.upper())
    if level:      query = query.filter(TBL_SYSTEM_LOG.level      == level.upper())
    if status:     query = query.filter(TBL_SYSTEM_LOG.status     == status.upper())
    if user_email: query = query.filter(TBL_SYSTEM_LOG.user_email.ilike(f"%{user_email}%"))
    if search:
        query = query.filter(
            or_(
                TBL_SYSTEM_LOG.description.ilike(f"%{search}%"),
                TBL_SYSTEM_LOG.action.ilike(f"%{search}%"),
                TBL_SYSTEM_LOG.user_email.ilike(f"%{search}%"),
            )
        )
    if date_from:
        query = query.filter(TBL_SYSTEM_LOG.created_at >= date_from)
    if date_to:
        query = query.filter(TBL_SYSTEM_LOG.created_at <= date_to)

    total = query.count()
    logs  = (
        query
        .order_by(TBL_SYSTEM_LOG.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    def serialize_log(log):
        return {
            "id":          str(log.id),
            "action":      log.action,
            "module":      log.module,
            "level":       log.level,
            "status":      log.status,
            "description": log.description,
            "user_email":  log.user_email,
            "user_role":   log.user_role,
            "entity_type": log.entity_type,
            "entity_id":   log.entity_id,
            "old_value":   log.old_value,
            "new_value":   log.new_value,
            "ip_address":  str(log.ip_address) if log.ip_address else None,
            "endpoint":    log.endpoint,
            "method":      log.method,
            "created_at":  log.created_at.isoformat() if log.created_at else None,
        }

    return response(
        ok          = True,
        status_code = 200,
        message     = "System logs retrieved",
        data        = {
            "total":  total,
            "limit":  limit,
            "offset": offset,
            "logs":   [serialize_log(l) for l in logs],
        },
    )


# GET /api/v1/admin/logs/stats
@router.get("/api/v1/admin/logs/stats", tags=["System Logs"])
def get_log_stats(
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    from datetime import datetime, timezone
    now   = datetime.now(timezone.utc)
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)

    total_today  = db.query(func.count(TBL_SYSTEM_LOG.id)).filter(
        TBL_SYSTEM_LOG.created_at >= today).scalar() or 0

    total_errors = db.query(func.count(TBL_SYSTEM_LOG.id)).filter(
        TBL_SYSTEM_LOG.level.in_(["ERROR", "CRITICAL"]),
        TBL_SYSTEM_LOG.created_at >= today).scalar() or 0

    total_warnings = db.query(func.count(TBL_SYSTEM_LOG.id)).filter(
        TBL_SYSTEM_LOG.level == "WARNING",
        TBL_SYSTEM_LOG.created_at >= today).scalar() or 0

    failed_logins = db.query(func.count(TBL_SYSTEM_LOG.id)).filter(
        TBL_SYSTEM_LOG.action == "USER_LOGIN_FAILED",
        TBL_SYSTEM_LOG.created_at >= today).scalar() or 0

    by_module = (
        db.query(TBL_SYSTEM_LOG.module, func.count(TBL_SYSTEM_LOG.id))
        .filter(TBL_SYSTEM_LOG.created_at >= today)
        .group_by(TBL_SYSTEM_LOG.module)
        .all()
    )

    return response(
        ok          = True,
        status_code = 200,
        message     = "Log stats retrieved",
        data        = {
            "today": {
                "total_events":  total_today,
                "errors":        total_errors,
                "warnings":      total_warnings,
                "failed_logins": failed_logins,
            },
            "by_module": [
                {"module": m, "count": c}
                for m, c in by_module
            ],
        },
    )


# DELETE /api/v1/admin/logs/cleanup
@router.delete("/api/v1/admin/logs/cleanup", tags=["System Logs"])
def cleanup_old_logs(
    days        : int           = Query(90, ge=30),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    from datetime import datetime, timezone, timedelta
    cutoff  = datetime.now(timezone.utc) - timedelta(days=days)
    deleted = db.query(TBL_SYSTEM_LOG).filter(
        TBL_SYSTEM_LOG.created_at < cutoff
    ).delete(synchronize_session=False)
    db.commit()

    return response(
        ok          = True,
        status_code = 200,
        message     = f"Deleted {deleted} logs older than {days} days",
        data        = {"deleted_count": deleted},
    )
