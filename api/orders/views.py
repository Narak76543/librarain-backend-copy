import logging
from decimal import Decimal
from fastapi import Depends, Query, BackgroundTasks
from fastapi.encoders import jsonable_encoder
from core.fcm import notify_order_status
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload
from starlette import status

import subprocess
import os
from fastapi import HTTPException, Depends
from fastapi.responses import StreamingResponse
from io import BytesIO

from api.orders.schemas import UpdateOrderStatusSchemas, PlaceOrderRequest
from core.db import get_db
from main import app
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user, require_admin
from api.cart.models import TBL_CART_ITEM
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM, TBL_ORDER_ITEM_BATCH_ALLOCATION
from api.inventory.models import TBL_INVENTORY_TRANSACTION, TBL_STOCK_BATCH
from fastapi import HTTPException, Path, Body
from sqlalchemy import func
from api.books.models import TBL_BOOK, TBL_STOCK_IN
from api.user_profile.models import TBL_USER_PROFILE
from core.logger import write_log, LogAction, LogModule
from api.telegram_bots.bot_polling import send_telegram_message_sync
from core.fcm import notify_order_placed, notify_order_status

logger = logging.getLogger(__name__)


def serialize_order(order: TBL_ORDER) -> dict:
    items = []
    for oi in order.order_items:
        price_at = Decimal(str(oi.price_at_purchase))
        items.append({
            "id":                str(oi.id),
            "book_id":           str(oi.book_id) if oi.book_id else None,
            "book_title":        oi.book.title     if oi.book else "Deleted book",
            "book_cover":        oi.book.cover_url if oi.book else None,
            "quantity":          oi.quantity,
            "price_at_purchase": str(price_at),
            "subtotal":          str(price_at * oi.quantity),
        })
    return {
        "id":               str(order.id),
        "total":            str(order.total),
        "status":           order.status,
        "delivery_way":     order.delivery_way,
        "delivery_partner": order.delivery_partner,
        "delivery_address": order.delivery_address,
        "payment_method":   order.payment_method,
        "created_at":       order.created_at.isoformat() if order.created_at else None,
        "order_items":      items,
    }


# ================= POST /orders =============================
@app.post("/api/v1/orders", tags=["Orders"])
def place_order(
    payload     : PlaceOrderRequest = Body(default=None),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    # Validation
    if payload and payload.delivery_way == "Delivery":
        if not payload.delivery_partner:
            return response(
                ok          = False,
                status_code = status.HTTP_400_BAD_REQUEST,
                message     = "Delivery partner is required when delivery way is Delivery",
            )
        if not payload.delivery_address or not payload.delivery_address.strip():
            return response(
                ok          = False,
                status_code = status.HTTP_400_BAD_REQUEST,
                message     = "Delivery address is required when delivery way is Delivery",
            )

    # Get all cart items
    cart_items = (
        db.query(TBL_CART_ITEM)
        .filter(TBL_CART_ITEM.user_id == current_user.id)
        .all()
    )

    if not cart_items:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Cart is empty",
        )

    # Calculate total dynamically using strict FIFO batches
    total = Decimal('0.00')
    split_items = []

    for cart_item in cart_items:
        qty_to_allocate = cart_item.quantity
        book = cart_item.book
        
        # Fetch active batches for this book
        batches = db.query(TBL_STOCK_BATCH).filter(
            TBL_STOCK_BATCH.book_id == book.id,
            TBL_STOCK_BATCH.remaining_quantity > 0,
            TBL_STOCK_BATCH.status == "active"
        ).order_by(TBL_STOCK_BATCH.received_at.asc()).all()
        
        if not batches:
            split_items.append({
                "book_id": book.id,
                "quantity": qty_to_allocate,
                "price": Decimal(str(book.price)),
                "cost": Decimal(str(book.cost_price))
            })
            total += Decimal(str(book.price)) * qty_to_allocate
            continue
            
        for batch in batches:
            if qty_to_allocate <= 0:
                break
                
            take_qty = min(batch.remaining_quantity, qty_to_allocate)
            
            margin_multiplier = Decimal('1.0') + (Decimal(str(book.min_profit_margin or 0)) / Decimal('100.0'))
            batch_sale_price = Decimal(str(batch.unit_cost_price)) * margin_multiplier
            
            split_items.append({
                "book_id": book.id,
                "quantity": take_qty,
                "price": batch_sale_price,
                "cost": Decimal(str(batch.unit_cost_price))
            })
            
            total += batch_sale_price * take_qty
            qty_to_allocate -= take_qty
            
        if qty_to_allocate > 0:
            split_items.append({
                "book_id": book.id,
                "quantity": qty_to_allocate,
                "price": Decimal(str(book.price)),
                "cost": Decimal(str(book.cost_price))
            })
            total += Decimal(str(book.price)) * qty_to_allocate

    # Create order
    order = TBL_ORDER(
        user_id          = current_user.id,
        total            = total,
        status           = "pending",
        delivery_way     = payload.delivery_way if payload else "Pick Up",
        delivery_partner = payload.delivery_partner if payload else None,
        delivery_address = payload.delivery_address if payload else None,
        payment_method   = payload.payment_method if payload else "COD",
    )
    db.add(order)
    db.flush()

    # Create order items — lock price_at_purchase based on split batches
    for split_item in split_items:
        order_item = TBL_ORDER_ITEM(
            order_id               = order.id,
            book_id                = split_item["book_id"],
            quantity               = split_item["quantity"],
            price_at_purchase      = split_item["price"],
            cost_price_at_purchase = split_item["cost"],
        )
        db.add(order_item)

    # Clear cart
    db.query(TBL_CART_ITEM).filter(
        TBL_CART_ITEM.user_id == current_user.id
    ).delete(synchronize_session=False)

    db.commit()
    db.refresh(order)

    notify_order_placed(
    db       = db,
    user_id  = current_user.id,
    order_id = str(order.id),
    total    = str(order.total),
)

    write_log(
        db          = db,
        action      = LogAction.ORDER_PLACED,
        module      = LogModule.ORDER,
        description = f"Order placed by {current_user.email} — total: ${order.total}",
        user_id     = current_user.id,
        user_email  = current_user.email,
        entity_type = "order",
        entity_id   = str(order.id),
        new_value   = {
            "order_id":    str(order.id),
            "total":       str(order.total),
            "items_count": len(order.order_items),
        },
        commit      = True,
    )

    # Trigger Telegram Alert for new order
    if current_user.telegram_chat_id:
        items_list = "\n".join([f"- {oi.book.title if oi.book else 'Deleted'} (x{oi.quantity})" for oi in order.order_items])
        
        if order.delivery_way == "Pick Up":
            delivery_details = (
                "🏪 *Pick Up at Shop*\n"
                "📍 *Address:* Librarain Main Shop, St 123, Phnom Penh\n"
                "🗺️ *Google Maps:* https://maps.app.goo.gl/X6JSrKwfBJzKY34aA"
            )
        else:
            delivery_details = (
                f"🚚 *Delivery* via {order.delivery_partner or 'Standard'}\n"
                f"🏢 *Address:* {order.delivery_address or 'Not specified'}"
            )
            
        msg = (
            f"📚 *Order Placed Successfully!*\n\n"
            f"Your Order `#{str(order.id)[:8].upper()}` is now *PENDING*!\n\n"
            f"*Delivery Details:*\n{delivery_details}\n\n"
            f"*Payment Method:*\n💰 *{order.payment_method}*\n\n"
            f"*Order Summary:*\n{items_list}\n\n"
            f"*Total:* ${order.total:.2f}\n\n"
            "Thank you for shopping with Librarain! 📚"
        )
        
        if background_tasks:
            background_tasks.add_task(send_telegram_message_sync, current_user.telegram_chat_id, msg)
        else:
            send_telegram_message_sync(current_user.telegram_chat_id, msg)

    return response(
        ok          = True,
        status_code = status.HTTP_201_CREATED,
        message     = "Order placed successfully",
        data        = serialize_order(order),
    )


# ================= GET /orders ==============================
@app.get("/api/v1/orders", tags=["Orders"])
def get_my_orders(
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    orders = (
        db.query(TBL_ORDER)
        .options(joinedload(TBL_ORDER.order_items).joinedload(TBL_ORDER_ITEM.book))
        .filter(TBL_ORDER.user_id == current_user.id)
        .order_by(TBL_ORDER.created_at.desc())
        .all()
    )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Orders retrieved successfully",
        data        = {
            "total":  len(orders),
            "orders": [serialize_order(o) for o in orders],
        },
    )


# ================= GET /orders/{id} =========================
@app.get("/api/v1/orders/{order_id}", tags=["Orders"])
def get_order_detail(
    order_id    : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    order = (
        db.query(TBL_ORDER)
        .options(joinedload(TBL_ORDER.order_items).joinedload(TBL_ORDER_ITEM.book))
        .filter(
            TBL_ORDER.id      == order_id,
            TBL_ORDER.user_id == current_user.id,
        )
        .first()
    )

    if not order:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Order not found",
        )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Order retrieved successfully",
        data        = serialize_order(order),
    )

# ==== admin : get admin order ==================
@app.get("/api/v1/admin/orders", tags=["Admin"])
def get_admin_orders(
    search    : str | None = Query(None),
    status    : str | None = Query(None, alias="status"),
    date_from : str | None = Query(None),
    date_to   : str | None = Query(None),
    limit     : int        = Query(10, ge=1, le=100),
    offset    : int        = Query(0, ge=0),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db        : Session    = Depends(get_db),
):
    query = db.query(TBL_ORDER).options(joinedload(TBL_ORDER.order_items).joinedload(TBL_ORDER_ITEM.book)).join(TBL_AUTH_USER)

    if search:
        query = query.filter(
            or_(
                TBL_AUTH_USER.full_name.ilike(f"%{search}%"),
                TBL_AUTH_USER.email.ilike(f"%{search}%"),
            )
        )
    if status:
        query = query.filter(TBL_ORDER.status == status)
    if date_from:
        query = query.filter(TBL_ORDER.created_at >= date_from)
    if date_to:
        if len(date_to) == 10:
            query = query.filter(TBL_ORDER.created_at <= f"{date_to} 23:59:59")
        else:
            query = query.filter(TBL_ORDER.created_at <= date_to)

    total  = query.count()
    orders = query.order_by(TBL_ORDER.created_at.desc()).offset(offset).limit(limit).all()

    def serialize_order(o):
        return {
            "id":               str(o.id),
            "customer": {
                "full_name": o.user.full_name,
                "email":     o.user.email,
            },
            "items_count":      len(o.order_items),
            "total":            str(o.total),
            "status":           o.status,
            "delivery_way":     o.delivery_way,
            "delivery_partner": o.delivery_partner,
            "delivery_address": o.delivery_address,
            "payment_method":   o.payment_method,
            "created_at":       o.created_at.isoformat(),
            "order_items": [
                {
                    "book_title": oi.book.title     if oi.book else "Deleted",
                    "book_cover": oi.book.cover_url if oi.book else None,
                    "quantity":   oi.quantity,
                    "price":      str(oi.price_at_purchase),
                    "subtotal":   str(oi.price_at_purchase * oi.quantity),
                }
                for oi in o.order_items
            ],
        }

    return response(
        ok          = True,
        status_code = 200,
        message     = "Orders retrieved successfully",
        data        = {
            "total":  total,
            "limit":  limit,
            "offset": offset,
            "orders": [serialize_order(o) for o in orders],
        },
    )

# ========================== Admin Update status ================================================
@app.patch ("/api/v1/admin/orders/{order_id}/status" , tags=['Admin'])
def update_order_status (
    order_id     : str                      = Path(... , description="The ID of order to update"),
    payload      : UpdateOrderStatusSchemas = Body(...),
    background_tasks : BackgroundTasks      = None,
    current_user : TBL_AUTH_USER            = Depends(require_admin),
    db           : Session                  = Depends(get_db)
) :
    order = db.query(TBL_ORDER).filter(TBL_ORDER.id == order_id).first()

    if not order : 
        raise HTTPException (
            status_code = 404,
            detail      = f"order with id '{order_id}' not found "
        )
        
    # Stock Adjustment on "delivered" or "completed"
    if payload.status.lower() in ("delivered", "completed") and order.status.lower() not in ("delivered", "completed"):
        for oi in order.order_items:
            if oi.book:
                qty_to_fulfill = oi.quantity
                total_cost_for_item = Decimal("0.00")
                
                # Fetch active batches (FIFO)
                batches = db.query(TBL_STOCK_BATCH).filter(
                    TBL_STOCK_BATCH.book_id == oi.book.id,
                    TBL_STOCK_BATCH.remaining_quantity > 0
                ).order_by(TBL_STOCK_BATCH.received_at.asc()).all()
                
                for batch in batches:
                    if qty_to_fulfill <= 0:
                        break
                        
                    take_qty = min(batch.remaining_quantity, qty_to_fulfill)
                    batch.remaining_quantity -= take_qty
                    qty_to_fulfill -= take_qty
                    
                    if batch.remaining_quantity == 0:
                        batch.status = "depleted"
                        # Strict FIFO Pricing: Update retail price to the NEXT active batch
                        next_batch = db.query(TBL_STOCK_BATCH).filter(
                            TBL_STOCK_BATCH.book_id == oi.book.id,
                            TBL_STOCK_BATCH.id != batch.id,
                            TBL_STOCK_BATCH.remaining_quantity > 0,
                            TBL_STOCK_BATCH.status == "active"
                        ).order_by(TBL_STOCK_BATCH.received_at.asc()).first()
                        
                        if next_batch:
                            margin_multiplier = 1.0 + (float(oi.book.min_profit_margin) / 100.0)
                            new_price = float(next_batch.unit_cost_price) * margin_multiplier
                            oi.book.price = new_price
                        
                    # Calculate cost for this portion
                    batch_cost = Decimal(str(take_qty)) * Decimal(str(batch.unit_cost_price))
                    total_cost_for_item += batch_cost
                    
                    # Create allocation record
                    allocation = TBL_ORDER_ITEM_BATCH_ALLOCATION(
                        order_item_id=oi.id,
                        stock_batch_id=batch.id,
                        quantity_allocated=take_qty,
                        unit_cost_price=batch.unit_cost_price
                    )
                    db.add(allocation)
                
                # Update blended cost_price
                if oi.quantity > 0:
                    oi.cost_price_at_purchase = total_cost_for_item / Decimal(str(oi.quantity))

                # Update global stock
                oi.book.stock = max(0, oi.book.stock - oi.quantity)
                transaction = TBL_INVENTORY_TRANSACTION(
                    book_id=oi.book.id,
                    transaction_type="sale",
                    quantity=-oi.quantity,
                    current_stock=oi.book.stock,
                    reference_id=str(order.id)
                )
                db.add(transaction)

    old_status = order.status
    order.status = payload.status.lower()

    try : 
        db.commit()
        db.refresh(order)

        if order.status in ("delivered", "completed"):
            from api.invoices.services import create_invoice_for_order
            try:
                create_invoice_for_order(db, order)
            except Exception as inv_err:
                logger.error(f"Failed to auto-generate invoice for order {order.id}: {inv_err}")

        if old_status != payload.status:
            notify_order_status(
                db         = db,
                user_id    = order.user_id,
                order_id   = str(order.id),
                new_status = payload.status,
            )

            write_log(
                db          = db,
                action      = LogAction.ORDER_STATUS_CHANGED,
                module      = LogModule.ORDER,
                description = f"Order #{str(order.id)[:8].upper()} status changed: {old_status} -> {payload.status}",
                user_id     = current_user.id,
                user_email  = current_user.email,
                user_role   = "ADMIN",
                entity_type = "order",
                entity_id   = str(order.id),
                old_value   = {"status": old_status},
                new_value   = {"status": payload.status},
                commit      = True,
            )

    except Exception as e :
        db.rollback()
        raise HTTPException (
            status_code = 500,
            detail      = "fail to update order status "
        )

    # Trigger Telegram Alert for status changes
    if order.user and order.user.telegram_chat_id:
        status_lower = payload.status.lower()
        emoji = "📦"
        status_text = payload.status.upper()
        if status_lower == "pending":
            emoji = "⏳"
        elif status_lower == "processing":
            emoji = "⚙️"
        elif status_lower == "delivered":
            emoji = "🚚"
        elif status_lower == "completed":
            emoji = "✅"
        elif status_lower == "cancelled":
            emoji = "❌"

        items_list = "\n".join([f"- {oi.book.title if oi.book else 'Deleted'} (x{oi.quantity})" for oi in order.order_items])
        delivery_details = "🏪 *Pick Up*"
        if order.delivery_way == "Delivery":
            delivery_details = f"🚚 *Delivery* via {order.delivery_partner or 'Standard'}"

        msg = (
            f"{emoji} *Order Status Update*\n\n"
            f"Your Order `#{str(order.id)[:8].upper()}` is now *{status_text}*!\n\n"
            f"*Delivery Details:*\n{delivery_details}\n\n"
            f"*Payment Method:*\n💰 *{order.payment_method}*\n\n"
            f"*Order Summary:*\n{items_list}\n\n"
            f"*Total:* ${order.total:.2f}\n\n"
            "Thank you for shopping with Librarain! 📚"
        )

        if background_tasks:
            background_tasks.add_task(send_telegram_message_sync, order.user.telegram_chat_id, msg)
        else:
            send_telegram_message_sync(order.user.telegram_chat_id, msg)

    return response (
        ok          = True,
        status_code = 200,
        message     = f"Order status updated to '{payload.status}' successfully",
        data        = {
            "order_id"  : str(order_id),
            "new_status": order.status
        }, 
    )

def calculate_trend(today_val, yesterday_val):
    if yesterday_val == 0 and today_val > 0:
        return "New"
    if yesterday_val == 0 and today_val == 0:
        return "0%"
    trend = ((today_val - yesterday_val) / yesterday_val) * 100
    return f"{'+' if trend > 0 else ''}{round(trend)}%"

@app.get("/api/v1/admin/dashboard", tags=["Admin"])
def get_dashboard_stats(
    period: str = Query("30d"),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    today = now.date()
    
    if period == "24h":
        start_date      = today
        prev_start_date = today - timedelta(days=1)
        prev_end_date   = today - timedelta(days=1)

    elif period == "7d":
        start_date      = today - timedelta(days=6)
        prev_start_date = today - timedelta(days=13)
        prev_end_date   = today - timedelta(days=7)

    elif period == "this_month":
        start_date = today.replace(day=1)
        prev_start_date = (start_date - timedelta(days=1)).replace(day=1)
        prev_end_date = start_date - timedelta(days=1)

    elif period == "prev_month":
        # ======= Target period is the previous calendar month =================
        target_start = (today.replace(day=1) - timedelta(days=1)).replace(day=1)
        target_end   = today.replace(day=1) - timedelta(days=1)
        
        start_date = target_start
          # Previous to the previous month
        prev_start_date = (target_start - timedelta(days=1)).replace(day=1)
        prev_end_date   = target_start - timedelta(days=1)
    else: # 30d
        start_date      = today - timedelta(days=29)
        prev_start_date = today - timedelta(days=59)
        prev_end_date   = today - timedelta(days=30)
        
    def filter_current(query, model):
        if period == "24h":
            return query.filter(func.date(model.created_at) == start_date)
        return query.filter(func.date(model.created_at) >= start_date)

    def filter_prev(query, model):
        if period == "24h":
            return query.filter(func.date(model.created_at) == prev_start_date)
        return query.filter(
            func.date(model.created_at) >= prev_start_date,
            func.date(model.created_at) <= prev_end_date
        )
    
    # 1. KPIs
    revenue_today = filter_current(db.query(func.sum(TBL_ORDER.total)), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0
    revenue_yesterday = filter_prev(db.query(func.sum(TBL_ORDER.total)), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0

    cost_today = filter_current(db.query(func.sum(TBL_ORDER_ITEM.cost_price_at_purchase * TBL_ORDER_ITEM.quantity)).join(TBL_ORDER), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0
    cost_yesterday = filter_prev(db.query(func.sum(TBL_ORDER_ITEM.cost_price_at_purchase * TBL_ORDER_ITEM.quantity)).join(TBL_ORDER), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0
    
    net_profit_today = revenue_today - cost_today
    net_profit_yesterday = revenue_yesterday - cost_yesterday
    
    books_sold_today = filter_current(db.query(func.sum(TBL_ORDER_ITEM.quantity)).join(TBL_ORDER), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0
    books_sold_yesterday = filter_prev(db.query(func.sum(TBL_ORDER_ITEM.quantity)).join(TBL_ORDER), TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).scalar() or 0
    
    inventory_value = db.query(func.sum(TBL_STOCK_BATCH.remaining_quantity * TBL_STOCK_BATCH.unit_cost_price)).filter(TBL_STOCK_BATCH.remaining_quantity > 0).scalar() or 0
    
    kpis = {
        "revenue_today"   : float(revenue_today),
        "revenue_trend"   : calculate_trend(revenue_today, revenue_yesterday),
        "cost_today"      : float(cost_today),
        "cost_trend"      : calculate_trend(cost_today, cost_yesterday),
        "net_profit"      : float(net_profit_today),
        "profit_trend"    : calculate_trend(net_profit_today, net_profit_yesterday),
        "books_sold"      : int(books_sold_today),
        "books_sold_trend": calculate_trend(books_sold_today, books_sold_yesterday),
        "inventory_value" : float(inventory_value)
    }

    # 2. Sales Overview (last 30 days or based on period)
    sales_overview = []
    if period == "24h":
        for i in range(23, -1, -1):
            h = (now - timedelta(hours=i)).replace(minute=0, second=0, microsecond=0)
            rev = db.query(func.sum(TBL_ORDER.total)).filter(
                func.lower(TBL_ORDER.status) == "completed",
                TBL_ORDER.created_at >= h,
                TBL_ORDER.created_at < h + timedelta(hours=1)
            ).scalar() or 0
            cst = db.query(func.sum(TBL_ORDER_ITEM.cost_price_at_purchase * TBL_ORDER_ITEM.quantity)).join(TBL_ORDER).filter(
                func.lower(TBL_ORDER.status) == "completed",
                TBL_ORDER.created_at >= h,
                TBL_ORDER.created_at < h + timedelta(hours=1)
            ).scalar() or 0
            sales_overview.append({
                "date": h.strftime("%H:00"),
                "revenue": float(rev),
                "cost": float(cst),
                "profit": float(rev - cst)
            })
    else:
        # Determine the target date range for the loop
        if period == "this_month":
            loop_start = start_date
            loop_end = today # only graph up to today to save empty future days
        elif period == "prev_month":
            loop_start = start_date
            loop_end = today.replace(day=1) - timedelta(days=1) # end of prev month
        elif period == "7d":
            loop_start = today - timedelta(days=6)
            loop_end = today
        else: # 30d
            loop_start = today - timedelta(days=29)
            loop_end = today
            
        current_date = loop_start
        while current_date <= loop_end:
            day = current_date
            rev = db.query(func.sum(TBL_ORDER.total)).filter(
                func.lower(TBL_ORDER.status) == "completed",
                func.date(TBL_ORDER.created_at) == day
            ).scalar() or 0
            cst = db.query(func.sum(TBL_ORDER_ITEM.cost_price_at_purchase * TBL_ORDER_ITEM.quantity)).join(TBL_ORDER).filter(
                func.lower(TBL_ORDER.status) == "completed",
                func.date(TBL_ORDER.created_at) == day
            ).scalar() or 0
            sales_overview.append({
                "date": day.strftime("%b %d"),
                "revenue": float(rev),
                "cost": float(cst),
                "profit": float(rev - cst)
            })
            current_date += timedelta(days=1)

    # 3. Stock In (Filtered)
    stock_in_query = filter_current(db.query(TBL_BOOK.title, func.sum(TBL_STOCK_IN.quantity).label('qty')).join(TBL_BOOK), TBL_STOCK_IN)\
        .group_by(TBL_BOOK.title).order_by(func.sum(TBL_STOCK_IN.quantity).desc()).limit(5).all()
    stock_in = [{"title": r[0], "quantity": int(r[1])} for r in stock_in_query]

    # 4. Stock Out (Filtered)
    stock_out_query = filter_current(db.query(TBL_BOOK.title, func.sum(TBL_ORDER_ITEM.quantity).label('qty')).join(TBL_BOOK).join(TBL_ORDER), TBL_ORDER)\
        .filter(func.lower(TBL_ORDER.status) == "completed")\
        .group_by(TBL_BOOK.title).order_by(func.sum(TBL_ORDER_ITEM.quantity).desc()).limit(5).all()
    stock_out = [{"title": r[0], "quantity": int(r[1])} for r in stock_out_query]

    # 5. Delivery & Payment Analytics (Filtered)
    delivery_rows = filter_current(db.query(TBL_ORDER.delivery_way, func.count(TBL_ORDER.id)), TBL_ORDER)\
        .group_by(TBL_ORDER.delivery_way).all()
    delivery_breakdown = [{"label": r[0], "value": int(r[1])} for r in delivery_rows]

    payment_rows = filter_current(db.query(TBL_ORDER.payment_method, func.count(TBL_ORDER.id)), TBL_ORDER)\
        .group_by(TBL_ORDER.payment_method).all()
    payment_breakdown = [{"label": r[0], "value": int(r[1])} for r in payment_rows]

    # 6. Best Selling Books (All time, top 5)
    best_sellers_query = db.query(
        TBL_BOOK.id,
        TBL_BOOK.title,
        TBL_BOOK.author,
        TBL_BOOK.cover_url,
        func.sum(TBL_ORDER_ITEM.quantity).label('qty'),
        func.sum(TBL_ORDER_ITEM.price_at_purchase * TBL_ORDER_ITEM.quantity).label('rev')
    ).join(TBL_ORDER_ITEM).join(TBL_ORDER).filter(
        func.lower(TBL_ORDER.status) == "completed"
    ).group_by(TBL_BOOK.id).order_by(func.sum(TBL_ORDER_ITEM.quantity).desc()).limit(5).all()
    
    best_sellers = []
    for r in best_sellers_query:
        qty_30d = db.query(func.sum(TBL_ORDER_ITEM.quantity)).join(TBL_ORDER).filter(
            TBL_ORDER_ITEM.book_id == r[0],
            func.lower(TBL_ORDER.status) == "completed",
            TBL_ORDER.created_at >= (today - timedelta(days=30))
        ).scalar() or 0
        qty_prev_30d = db.query(func.sum(TBL_ORDER_ITEM.quantity)).join(TBL_ORDER).filter(
            TBL_ORDER_ITEM.book_id == r[0],
            func.lower(TBL_ORDER.status) == "completed",
            TBL_ORDER.created_at >= (today - timedelta(days=60)),
            TBL_ORDER.created_at < (today - timedelta(days=30))
        ).scalar() or 0
        
        trend_val = calculate_trend(qty_30d, qty_prev_30d)
        
        best_sellers.append({
            "title": r[1],
            "author": r[2],
            "cover_url": r[3],
            "sold": int(r[4]),
            "revenue": float(r[5]),
            "trend": trend_val
        })

    # 7. Profit Breakdown (Today)
    profit_breakdown = {
        "revenue"   : float(revenue_today),
        "cost"      : float(cost_today),
        "net_profit": float(net_profit_today)
    }

    return response(
        ok=True,
        status_code=200,
        message="Dashboard stats retrieved successfully",
        data={
            "kpis"              : kpis,
            "sales_overview"    : sales_overview,
            "stock_in"          : stock_in,
            "stock_out"         : stock_out,
            "delivery_breakdown": delivery_breakdown,
            "payment_breakdown" : payment_breakdown,
            "best_sellers"      : best_sellers,
            "profit_breakdown"  : profit_breakdown
        }
    )

# ================= GET /orders/{id}/summary =================
@app.get("/api/v1/orders/{order_id}/summary", tags=["Orders"])
def get_order_summary(
    order_id    : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    order = (
        db.query(TBL_ORDER)
        .options(joinedload(TBL_ORDER.order_items).joinedload(TBL_ORDER_ITEM.book).joinedload(TBL_BOOK.category))
        .filter(
            TBL_ORDER.id      == order_id,
            TBL_ORDER.user_id == current_user.id,
        )
        .first()
    )

    if not order:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Order not found",
        )

    # Calculate subtotal
    subtotal = sum(
        oi.price_at_purchase * oi.quantity
        for oi in order.order_items
    )

    # ===== Serialize order items ===========
    items = [
        {
            "id"               : str(oi.id),
            "book_id"          : str(oi.book_id) if oi.book_id else None,
            "book_title"       : oi.book.title     if oi.book else "Deleted book",
            "book_author"      : oi.book.author    if oi.book else None,
            "book_cover"       : oi.book.cover_url if oi.book else None,
            "category_name"    : oi.book.category.name if oi.book and oi.book.category else None,
            "quantity"         : oi.quantity,
            "price_at_purchase": str(oi.price_at_purchase),
            "subtotal"         : str(oi.price_at_purchase * oi.quantity),
        }
        for oi in order.order_items
    ]

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Order summary retrieved successfully",
        data        = {
            "order": {
                "id"              : str(order.id),
                "short_id"        : str(order.id)[:8].upper(),
                "status"          : order.status,
                "created_at"      : order.created_at.strftime("%b %d, %Y %H:%M") if order.created_at else None,
                "delivery_way"    : order.delivery_way,
                "delivery_partner": order.delivery_partner,
                "delivery_address": order.delivery_address,
                "payment_method"  : order.payment_method,
            },
            "customer": {
                "full_name": current_user.full_name,
                "email"    : current_user.email,
                "phone"    : current_user.phone,
            },
            "items":       items,
            "item_count":  len(items),
            "summary": {
                "subtotal": str(subtotal),
                "discount": "0.00",             # ===== extend later for promo codes ===
                "delivery": "0.00",             # ===== free delivery for now ==========
                "total"   : str(order.total),
            },
        },
    )

# ======= Invoice ========= 
import io
from fastapi.responses import StreamingResponse
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT


# ================= GET /orders/{id}/invoice =================
@app.get("/api/v1/orders/{order_id}/invoice", tags=["Orders"])
def download_invoice(
    order_id    : str,
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db),
):
    order = (
        db.query(TBL_ORDER)
        .options(joinedload(TBL_ORDER.order_items).joinedload(TBL_ORDER_ITEM.book))
        .filter(
            TBL_ORDER.id      == order_id,
            TBL_ORDER.user_id == current_user.id,
        )
        .first()
    )

    if not order:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Order not found",
        )

    # ======= Build PDF ============================
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer,
        pagesize     = A4,
        rightMargin  = 20 * mm,
        leftMargin   = 20 * mm,
        topMargin    = 20 * mm,
        bottomMargin = 20 * mm,
    )

    styles   = getSampleStyleSheet()
    GREEN    = colors.HexColor("#059669")
    DARK     = colors.HexColor("#1C1C1E")
    GRAY     = colors.HexColor("#6B7280")
    LIGHT    = colors.HexColor("#F9FAFB")
    elements = []

    # ── Header ──
    header_style = ParagraphStyle(
        "header",
        fontSize  = 24,
        textColor = GREEN,
        fontName  = "Helvetica-Bold",
        alignment = TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "sub",
        fontSize  = 10,
        textColor = GRAY,
        fontName  = "Helvetica",
        alignment = TA_LEFT,
    )
    right_style = ParagraphStyle(
        "right",
        fontSize  = 10,
        textColor = GRAY,
        fontName  = "Helvetica",
        alignment = TA_RIGHT,
    )
    bold_style = ParagraphStyle(
        "bold",
        fontSize  = 11,
        textColor = DARK,
        fontName  = "Helvetica-Bold",
    )

    # App name + Invoice label
    header_data = [
        [
            Paragraph("📚 Librarain", header_style),
            Paragraph(
                f"<b>INVOICE</b><br/>"
                f"#{str(order.id)[:8].upper()}<br/>"
                f"{order.created_at.strftime('%B %d, %Y') if order.created_at else ''}",
                right_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[90*mm, 80*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=8))

    # ── Customer Info ──
    elements.append(Paragraph("Bill To:", ParagraphStyle("label", fontSize=9, textColor=GRAY, fontName="Helvetica")))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(current_user.full_name, bold_style))
    elements.append(Paragraph(current_user.email,     sub_style))
    if current_user.phone:
        elements.append(Paragraph(current_user.phone, sub_style))
    elements.append(Spacer(1, 6*mm))

    # =============== Order status ==================
    status_color = {
        "pending":    "#1D4ED8",
        "processing": "#B45309",
        "delivered":  "#059669",
        "completed":  "#059669",
        "cancelled":  "#DC2626",
    }.get(order.status.lower(), "#6B7280")

    elements.append(Paragraph(
        f'Status: <font color="{status_color}"><b>{order.status.upper()}</b></font>',
        ParagraphStyle("status", fontSize=10, fontName="Helvetica", textColor=DARK)
    ))
    elements.append(Spacer(1, 6*mm))

    # ====== Items table ============
    elements.append(Paragraph("Order Items", bold_style))
    elements.append(Spacer(1, 3*mm))

    table_data  = [["#", "Book Title", "Author", "Qty", "Unit Price", "Subtotal"]]
    for i, oi in enumerate(order.order_items, 1):
        table_data.append([
            str(i),
            oi.book.title  if oi.book else "Deleted book",
            oi.book.author if oi.book else "—",
            str(oi.quantity),
            f"${oi.price_at_purchase:.2f}",
            f"${oi.price_at_purchase * oi.quantity:.2f}",
        ])

    items_table = Table(
        table_data,
        colWidths = [8*mm, 55*mm, 40*mm, 12*mm, 22*mm, 22*mm],
    )
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",   (0,0), (-1,0), GREEN),
        ("TEXTCOLOR",    (0,0), (-1,0), colors.white),
        ("FONTNAME",     (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,0), 9),
        ("ALIGN",        (0,0), (-1,0), "CENTER"),
        ("BOTTOMPADDING",(0,0), (-1,0), 6),
        ("TOPPADDING",   (0,0), (-1,0), 6),
        # Data rows
        ("FONTNAME",     (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",     (0,1), (-1,-1), 9),
        ("TEXTCOLOR",    (0,1), (-1,-1), DARK),
        ("ALIGN",        (3,1), (-1,-1), "CENTER"),
        ("ALIGN",        (4,1), (-1,-1), "RIGHT"),
        ("ALIGN",        (5,1), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, LIGHT]),
        ("TOPPADDING",   (0,1), (-1,-1), 5),
        ("BOTTOMPADDING",(0,1), (-1,-1), 5),
        # Grid
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
        ("ROUNDEDCORNERS", [3]),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6*mm))

    # ============= Summary ======================
    subtotal = sum(oi.price_at_purchase * oi.quantity for oi in order.order_items)

    summary_data = [
        ["",              "Subtotal:",  f"${subtotal:.2f}"],
        ["",              "Discount:",  "$0.00"],
        ["",              "Delivery:",  "FREE"],
        ["",              "",           ""],
        ["",              "TOTAL:",     f"${order.total:.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[110*mm, 30*mm, 19*mm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,-2), "Helvetica"),
        ("FONTNAME",     (1,4), (-1,4),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 10),
        ("TEXTCOLOR",    (1,0), (1,-1),  GRAY),
        ("TEXTCOLOR",    (2,0), (2,3),   DARK),
        ("TEXTCOLOR",    (1,4), (-1,4),  GREEN),
        ("FONTSIZE",     (1,4), (-1,4),  12),
        ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
        ("LINEABOVE",    (1,4), (-1,4),  1, GREEN),
        ("TOPPADDING",   (0,4), (-1,4),  6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8*mm))

    # ── Footer ──
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Thank you for shopping with Librarain! 📚",
        ParagraphStyle("footer", fontSize=9, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER)
    ))
    elements.append(Paragraph(
        "For support contact: support@librarain.com",
        ParagraphStyle("footer2", fontSize=8, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER)
    ))

    # =========== Generate PDF =====================
    doc.build(elements)
    buffer.seek(0)

    filename = f"invoice_{str(order.id)[:8].upper()}.pdf"

    return StreamingResponse(
        buffer,
        media_type = "application/pdf",
        headers    = {
            "Content-Disposition": f"attachment; filename={filename}",
        },
    )