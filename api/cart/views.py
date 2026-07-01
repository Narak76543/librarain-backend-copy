import logging
from decimal import Decimal
from fastapi import Depends, Request
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session, joinedload
from starlette import status

from core.db import get_db
from main import app
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user
from api.cart.models import TBL_CART_ITEM
from api.cart import schemas
from api.books.models import TBL_BOOK
from core.logger import write_log, LogAction, LogModule

logger = logging.getLogger(__name__)

def serialize_cart_item(item: TBL_CART_ITEM) -> dict:
    price    = Decimal(str(item.book.price)) if item.book else Decimal("0")
    subtotal = price * item.quantity
    return {
        "id":         str(item.id),
        "book_id":    str(item.book_id),
        "quantity":   item.quantity,
        "book_title": item.book.title     if item.book else None,
        "book_cover": item.book.cover_url if item.book else None,
        "book_price": str(price),
        "subtotal":   str(subtotal),
        "created_at": item.created_at.isoformat() if item.created_at else None,
    }


# ================= GET /cart ================================
@app.get("/api/v1/cart", tags=["Cart"])
def get_cart(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    items = (
        db.query(TBL_CART_ITEM)
        .options(joinedload(TBL_CART_ITEM.book))
        .filter(TBL_CART_ITEM.user_id == current_user.id)
        .all()
    )

    serialized = [serialize_cart_item(i) for i in items]
    total      = sum(Decimal(i["subtotal"]) for i in serialized)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Cart retrieved successfully",
        data        = {
            "items":      serialized,
            "total":      str(total),
            "item_count": len(items),
        },
    )


# ================= POST /cart/items =========================
@app.post("/api/v1/cart/items", tags=["Cart"])
def add_to_cart(
    request     : Request,
    payload     : schemas.CartItemCreate,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    # Check book exists and is in stock
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

    if book.stock < payload.quantity:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = f"Not enough stock. Available: {book.stock}",
        )

    # Check if already in cart — update qty instead
    existing = (
        db.query(TBL_CART_ITEM)
        .filter(
            TBL_CART_ITEM.user_id == current_user.id,
            TBL_CART_ITEM.book_id == payload.book_id,
        )
        .first()
    )

    if existing:
        new_qty = existing.quantity + payload.quantity
        if book.stock < new_qty:
            return response(
                ok          = False,
                status_code = status.HTTP_400_BAD_REQUEST,
                message     = f"Not enough stock. Available: {book.stock}",
            )
        existing.quantity = new_qty
        db.commit()
        db.refresh(existing)
        return response(
            ok          = True,
            status_code = status.HTTP_200_OK,
            message     = "Cart item quantity updated",
            data        = serialize_cart_item(existing),
        )

    # Add new cart item
    cart_item = TBL_CART_ITEM(
        user_id  = current_user.id,
        book_id  = payload.book_id,
        quantity = payload.quantity,
    )
    db.add(cart_item)
    db.commit()
    db.refresh(cart_item)

    write_log(
        db          = db,
        action      = LogAction.CART_ITEM_ADDED,
        module      = LogModule.CART,
        description = f"Added {payload.quantity} of '{book.title}' to cart",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "cart_item",
        entity_id   = str(book.id),
        new_value   = {"book_id": str(book.id), "quantity": payload.quantity},
        request     = request,
        commit      = True,
    )

    return response(
        ok          = True,
        status_code = status.HTTP_201_CREATED,
        message     = "Book added to cart",
        data        = serialize_cart_item(cart_item),
    )


# ================= PUT /cart/items/{id} =====================
@app.put("/api/v1/cart/items/{item_id}", tags=["Cart"])
def update_cart_item(
    item_id     : str,
    payload     : schemas.CartItemUpdate,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    item = (
        db.query(TBL_CART_ITEM)
        .filter(
            TBL_CART_ITEM.id      == item_id,
            TBL_CART_ITEM.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Cart item not found",
        )

    if item.book.stock < payload.quantity:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = f"Not enough stock. Available: {item.book.stock}",
        )

    item.quantity = payload.quantity
    db.commit()
    db.refresh(item)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Cart item updated",
        data        = serialize_cart_item(item),
    )


# ================= DELETE /cart/items/{id} ==================
@app.delete("/api/v1/cart/items/{item_id}", tags=["Cart"])
def remove_cart_item(
    request     : Request,
    item_id     : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    item = (
        db.query(TBL_CART_ITEM)
        .filter(
            TBL_CART_ITEM.id      == item_id,
            TBL_CART_ITEM.user_id == current_user.id,
        )
        .first()
    )

    if not item:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Cart item not found",
        )

    book_id = item.book_id
    db.delete(item)
    db.commit()

    write_log(
        db          = db,
        action      = LogAction.CART_ITEM_REMOVED,
        module      = LogModule.CART,
        description = f"Removed item {book_id} from cart",
        user_id     = current_user.id,
        user_email  = current_user.email,
        user_role   = "USER",
        entity_type = "cart_item",
        entity_id   = str(book_id),
        request     = request,
        commit      = True,
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Item removed from cart",
    )


# ================= DELETE /cart =============================
@app.delete("/api/v1/cart", tags=["Cart"])
def clear_cart(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    db.query(TBL_CART_ITEM).filter(
        TBL_CART_ITEM.user_id == current_user.id
    ).delete(synchronize_session=False)
    db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Cart cleared",
    )