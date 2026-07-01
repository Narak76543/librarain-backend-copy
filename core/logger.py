from sqlalchemy.orm import Session
from fastapi import Request
from api.system_log.models import TBL_SYSTEM_LOG
import logging

logger = logging.getLogger(__name__)


def write_log(
    db         : Session,
    action     : str,
    module     : str,
    description: str,
    level      : str  = "INFO",
    status     : str  = "SUCCESS",
    user_id          = None,
    user_email : str  = None,
    user_role  : str  = None,
    entity_type: str  = None,
    entity_id  : str  = None,
    old_value  : dict = None,
    new_value  : dict = None,
    request    : Request = None,
    commit     : bool = False,
):
    try:
        log = TBL_SYSTEM_LOG(
            user_id     = user_id,
            user_email  = user_email,
            user_role   = user_role,
            action      = action,
            module      = module,
            level       = level,
            status      = status,
            description = description,
            entity_type = entity_type,
            entity_id   = str(entity_id) if entity_id else None,
            old_value   = old_value,
            new_value   = new_value,
            ip_address  = _get_ip(request)  if request else None,
            user_agent  = request.headers.get("user-agent") if request else None,
            endpoint    = str(request.url.path) if request else None,
            method      = request.method if request else None,
        )
        db.add(log)
        if commit:
            db.commit()
    except Exception as e:
        logger.exception(f"Failed to write system log: {e}")


def _get_ip(request: Request) -> str | None:
    if not request:
        return None
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


# ── Action constants ──────────────────────────────────────
class LogAction:
    # Auth
    USER_REGISTERED        = "USER_REGISTERED"
    USER_LOGIN_SUCCESS     = "USER_LOGIN_SUCCESS"
    USER_LOGIN_FAILED      = "USER_LOGIN_FAILED"
    USER_LOGOUT            = "USER_LOGOUT"
    PASSWORD_RESET_REQUEST = "PASSWORD_RESET_REQUEST"
    PASSWORD_RESET_SUCCESS = "PASSWORD_RESET_SUCCESS"
    ACCOUNT_LOCKED         = "ACCOUNT_LOCKED"
    ACCOUNT_UNLOCKED       = "ACCOUNT_UNLOCKED"

    # Orders
    ORDER_PLACED           = "ORDER_PLACED"
    ORDER_STATUS_CHANGED   = "ORDER_STATUS_CHANGED"
    ORDER_CANCELLED        = "ORDER_CANCELLED"

    # Books
    BOOK_CREATED           = "BOOK_CREATED"
    BOOK_UPDATED           = "BOOK_UPDATED"
    BOOK_DELETED           = "BOOK_DELETED"
    BOOK_COVER_UPLOADED    = "BOOK_COVER_UPLOADED"
    BOOK_FEATURED_TOGGLED  = "BOOK_FEATURED_TOGGLED"

    # Categories
    CATEGORY_CREATED       = "CATEGORY_CREATED"
    CATEGORY_UPDATED       = "CATEGORY_UPDATED"
    CATEGORY_DELETED       = "CATEGORY_DELETED"

    # Profile
    PROFILE_UPDATED        = "PROFILE_UPDATED"
    AVATAR_UPLOADED        = "AVATAR_UPLOADED"

    # Admin
    ADMIN_LOGIN            = "ADMIN_LOGIN"
    ADMIN_REPORT_EXPORTED  = "ADMIN_REPORT_EXPORTED"
    ADMIN_BACKUP_DOWNLOADED= "ADMIN_BACKUP_DOWNLOADED"
    ADMIN_RESET_ATTEMPT    = "ADMIN_RESET_ATTEMPT"
    ADMIN_FORCE_LOGOUT     = "ADMIN_FORCE_LOGOUT"
    ADMIN_STATUS_CHANGED   = "ADMIN_USER_STATUS_CHANGED"

    # Stock
    STOCK_ADJUSTED         = "STOCK_ADJUSTED"
    PO_CREATED             = "PURCHASE_ORDER_CREATED"
    PO_RECEIVED            = "PURCHASE_ORDER_RECEIVED"

    # Cart
    CART_ITEM_ADDED        = "CART_ITEM_ADDED"
    CART_ITEM_REMOVED      = "CART_ITEM_REMOVED"
    CART_CLEARED           = "CART_CLEARED"

    # Wishlist
    WISHLIST_ADDED         = "WISHLIST_ADDED"
    WISHLIST_REMOVED       = "WISHLIST_REMOVED"


class LogModule:
    AUTH     = "AUTH"
    ORDER    = "ORDER"
    BOOK     = "BOOK"
    CATEGORY = "CATEGORY"
    PROFILE  = "PROFILE"
    ADMIN    = "ADMIN"
    STOCK    = "STOCK"
    CART     = "CART"
    WISHLIST = "WISHLIST"
    SYSTEM   = "SYSTEM"
