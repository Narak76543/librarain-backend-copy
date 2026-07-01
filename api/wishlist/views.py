import logging
from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from starlette import status
from core.db import get_db
from main import app
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user
from api.wishlist.models import TBL_WISHLIST
from api.wishlist import schemas
from api.books.models import TBL_BOOK
from core.logger import write_log, LogAction, LogModule

from fastapi import Request

logger = logging.getLogger(__name__)


def serialize_wishlist_item(item: TBL_WISHLIST) -> dict:
    return {
        "id":            str(item.id),
        "book_id":       str(item.book_id),
        "book_title":    item.book.title                       if item.book else None,
        "book_author":   item.book.author                      if item.book else None,
        "book_cover":    item.book.cover_url                   if item.book else None,
        "book_price":    str(item.book.price)                  if item.book else None,
        "book_rating":   str(item.book.rating_average)         if item.book else None,
        "category_name": item.book.category.name               if item.book and item.book.category else None,
        "created_at":    item.created_at.isoformat()           if item.created_at else None,
    }


# ================= GET /wishlist ============================
@app.get("/api/v1/wishlist", tags=["Wishlist"])
def get_wishlist(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    items = (
        db.query(TBL_WISHLIST)
        .filter(TBL_WISHLIST.user_id == current_user.id)
        .order_by(TBL_WISHLIST.created_at.desc())
        .all()
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Wishlist retrieved successfully",
        data        = {
            "total": len(items),
            "items": [serialize_wishlist_item(i) for i in items],
        },
    )


# ================= POST /wishlist ===========================
@app.post("/api/v1/wishlist", tags=["Wishlist"])
def add_to_wishlist(
    request     : Request,
    payload     : schemas.WishlistAddRequest,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    # Check book exists
    book = (
        db.query(TBL_BOOK)
        .filter(
            TBL_BOOK.id       == payload.book_id,
            TBL_BOOK.is_active.is_(True),
        )
        .first()
    )

    if not book:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Book not found",
        )

    # Check already in wishlist
    existing = (
        db.query(TBL_WISHLIST)
        .filter(
            TBL_WISHLIST.user_id == current_user.id,
            TBL_WISHLIST.book_id == payload.book_id,
        )
        .first()
    )

    if existing:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Book already in wishlist",
        )

    item = TBL_WISHLIST(
        user_id = current_user.id,
        book_id = payload.book_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    write_log(
        db          = db,
        action      = LogAction.WISHLIST_ADDED,
        module      = LogModule.WISHLIST,
        description = f"Added '{book.title}' to wishlist",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "wishlist_item",
        entity_id   = str(book.id),
        new_value   = {"book_id": str(book.id)},
        request     = request,
        commit      = True,
    )

    return response(
        ok          = True,
        status_code = status.HTTP_201_CREATED,
        message     = "Book added to wishlist",
        data        = serialize_wishlist_item(item),
    )


# ================= DELETE /wishlist/{book_id} ===============
@app.delete("/api/v1/wishlist/{book_id}", tags=["Wishlist"])
def remove_from_wishlist(
    request     : Request,
    book_id     : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    item = (
        db.query(TBL_WISHLIST)
        .filter(
            TBL_WISHLIST.user_id == current_user.id,
            TBL_WISHLIST.book_id == book_id,
        )
        .first()
    )

    if not item:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Book not in wishlist",
        )

    db.delete(item)
    db.commit()

    write_log(
        db          = db,
        action      = LogAction.WISHLIST_REMOVED,
        module      = LogModule.WISHLIST,
        description = f"Removed book from wishlist",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "wishlist_item",
        entity_id   = str(book_id),
        request     = request,
        commit      = True,
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Book removed from wishlist",
    )


# ================= GET /wishlist/{book_id}/check ============
@app.get("/api/v1/wishlist/{book_id}/check", tags=["Wishlist"])
def check_wishlist(
    book_id     : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    exists = (
        db.query(TBL_WISHLIST)
        .filter(
            TBL_WISHLIST.user_id == current_user.id,
            TBL_WISHLIST.book_id == book_id,
        )
        .first()
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Wishlist status checked",
        data        = {
            "is_wishlisted": exists is not None,
            "book_id":       book_id,
        },
    )


# ================= POST /wishlist/toggle ====================
# Convenience endpoint — adds if not exists, removes if exists
@app.post("/api/v1/wishlist/toggle", tags=["Wishlist"])
def toggle_wishlist(
    request     : Request,
    payload     : schemas.WishlistAddRequest,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    existing = (
        db.query(TBL_WISHLIST)
        .filter(
            TBL_WISHLIST.user_id == current_user.id,
            TBL_WISHLIST.book_id == payload.book_id,
        )
        .first()
    )

    if existing:
        db.delete(existing)
        db.commit()
        write_log(
            db          = db,
            action      = LogAction.WISHLIST_REMOVED,
            module      = LogModule.WISHLIST,
            description = f"Removed book from wishlist",
            user_id     = current_user.id,
            user_email  = current_user.email,
            user_role   = "USER",
            entity_type = "wishlist_item",
            entity_id   = str(payload.book_id),
            request     = request,
            commit      = True,
        )
        return response(
            ok          = True,
            status_code = status.HTTP_200_OK,
            message     = "Removed from wishlist",
            data        = {"is_wishlisted": False, "book_id": str(payload.book_id)},
        )

    book = (
        db.query(TBL_BOOK)
        .filter(TBL_BOOK.id == payload.book_id, TBL_BOOK.is_active.is_(True))
        .first()
    )

    if not book:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Book not found",
        )

    item = TBL_WISHLIST(user_id=current_user.id, book_id=payload.book_id)
    db.add(item)
    db.commit()
    db.refresh(item)

    write_log(
        db          = db,
        action      = LogAction.WISHLIST_ADDED,
        module      = LogModule.WISHLIST,
        description = f"Added '{book.title}' to wishlist",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "wishlist_item",
        entity_id   = str(book.id),
        new_value   = {"book_id": str(book.id)},
        request     = request,
        commit      = True,
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Added to wishlist",
        data        = {"is_wishlisted": True, "book_id": str(payload.book_id)},
    )