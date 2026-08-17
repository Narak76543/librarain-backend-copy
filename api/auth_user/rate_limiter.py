
from datetime import datetime, timezone
from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.auth_user.models import TBL_REGISTRATION_RATE_LIMIT


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _window_start(now: datetime, seconds: int) -> datetime:
    epoch_seconds = int(now.timestamp())
    bucket = epoch_seconds - (epoch_seconds % seconds)
    return datetime.fromtimestamp(bucket, tz=timezone.utc)


def enforce_rate_limit(
    db            : Session,
    scope_type    : str,
    scope_value   : str,
    max_hits      : int,
    window_seconds: int,
) -> None:

    now = datetime.now(timezone.utc)
    window = _window_start(now, window_seconds)

    row = (
        db.query(TBL_REGISTRATION_RATE_LIMIT)
        .filter(
            TBL_REGISTRATION_RATE_LIMIT.scope_type == scope_type,
            TBL_REGISTRATION_RATE_LIMIT.scope_value == scope_value,
            TBL_REGISTRATION_RATE_LIMIT.window_start == window,
        )
        .with_for_update()
        .first()
    )

    if row is None:
        row = TBL_REGISTRATION_RATE_LIMIT(
            scope_type=scope_type,
            scope_value=scope_value,
            window_start=window,
            hit_count=1,
        )
        db.add(row)
        try:
            db.flush()
        except IntegrityError:
            db.rollback()
            row = (
                db.query(TBL_REGISTRATION_RATE_LIMIT)
                .filter(
                    TBL_REGISTRATION_RATE_LIMIT.scope_type == scope_type,
                    TBL_REGISTRATION_RATE_LIMIT.scope_value == scope_value,
                    TBL_REGISTRATION_RATE_LIMIT.window_start == window,
                )
                .with_for_update()
                .first()
            )
            row.hit_count += 1
    else:
        row.hit_count += 1

    if row.hit_count > max_hits:
        db.commit()
        raise HTTPException(
            status_code = status.HTTP_429_TOO_MANY_REQUESTS,
            detail      = "Too many requests. Please try again later.",
        )

    db.commit()


def enforce_registration_limits(db: Session, request: Request, email: str) -> None:
    """1 request/min AND max 10 within 10 minutes, per IP and per email."""
    ip = get_client_ip(request)
    enforce_rate_limit(db, "IP", ip, max_hits=1, window_seconds=60)
    enforce_rate_limit(db, "IP", ip, max_hits=10, window_seconds=600)
    enforce_rate_limit(db, "EMAIL", email.lower(), max_hits=1, window_seconds=60)
    enforce_rate_limit(db, "EMAIL", email.lower(), max_hits=10, window_seconds=600)