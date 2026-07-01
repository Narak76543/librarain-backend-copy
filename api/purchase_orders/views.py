from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Any
from datetime import datetime

from core.db import get_db
from api.auth_user.security import get_current_user
from api.auth_user.models import TBL_AUTH_USER
from api.books.models import TBL_BOOK, TBL_STOCK_HISTORY
from api.suppliers.models import TBL_SUPPLIER
from api.inventory.models import TBL_INVENTORY_TRANSACTION, TBL_STOCK_BATCH
from .models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM
from .schemas import PurchaseOrderCreate, PurchaseOrderStatusUpdate, PurchaseOrderResponse

router = APIRouter(prefix="/api/v1/purchase-orders", tags=["Purchase Orders"])

def generate_po_number(db: Session) -> str:
    current_year = datetime.now().year
    prefix = f"PO-{current_year}-"
    # Find the latest PO number for the current year
    latest_po = db.query(TBL_PURCHASE_ORDER).filter(TBL_PURCHASE_ORDER.po_number.startswith(prefix)).order_by(TBL_PURCHASE_ORDER.po_number.desc()).first()
    
    if latest_po:
        last_num = int(latest_po.po_number.split("-")[-1])
        new_num = last_num + 1
    else:
        new_num = 1
        
    return f"{prefix}{new_num:05d}"

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_purchase_order(
    payload: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to create purchase orders")
    
    supplier = db.query(TBL_SUPPLIER).filter(TBL_SUPPLIER.id == payload.supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    po_number = generate_po_number(db)
    total_cost = sum(item.quantity * item.cost_price for item in payload.items)

    po = TBL_PURCHASE_ORDER(
        po_number=po_number,
        supplier_id=payload.supplier_id,
        total_cost=total_cost,
        status="pending",
        ordered_at=datetime.now(),
        note=payload.note,
        created_by=current_user.id
    )
    db.add(po)
    db.flush() # To get po.id

    for item in payload.items:
        book = db.query(TBL_BOOK).filter(TBL_BOOK.id == item.book_id).first()
        if not book:
            db.rollback()
            raise HTTPException(status_code=404, detail=f"Book not found: {item.book_id}")

        po_item = TBL_PURCHASE_ORDER_ITEM(
            po_id=po.id,
            book_id=item.book_id,
            quantity=item.quantity,
            cost_price=item.cost_price,
            total_cost=item.quantity * item.cost_price
        )
        db.add(po_item)
    
    db.commit()
    db.refresh(po)
    
    return {
        "ok": True,
        "status": 201,
        "message": "Purchase Order created successfully",
        "data": {"id": str(po.id), "po_number": po.po_number}
    }

@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def list_purchase_orders(
    skip: int = 0,
    limit: int = 100,
    period: str = None,
    status_filter: str = None,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to view POs")

    query = db.query(TBL_PURCHASE_ORDER)
    
    if status_filter and status_filter.lower() != "all":
        query = query.filter(TBL_PURCHASE_ORDER.status == status_filter.lower())
        
    if period:
        from datetime import timedelta
        now = datetime.now()
        if period == '24h':
            start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.filter(TBL_PURCHASE_ORDER.created_at >= start_of_day)
        elif period == '7d':
            query = query.filter(TBL_PURCHASE_ORDER.created_at >= now - timedelta(days=7))
        elif period == '30d':
            query = query.filter(TBL_PURCHASE_ORDER.created_at >= now - timedelta(days=30))

    total = query.count()
    pos = query.order_by(TBL_PURCHASE_ORDER.created_at.desc()).offset(skip).limit(limit).all()

    # format response
    results = []
    for po in pos:
        po_data = {
            "id": str(po.id),
            "po_number": po.po_number,
            "supplier_id": str(po.supplier_id),
            "supplier_name": po.supplier.name if po.supplier else "Unknown",
            "total_cost": float(po.total_cost),
            "status": po.status,
            "ordered_at": po.ordered_at.isoformat() if po.ordered_at else None,
            "received_at": po.received_at.isoformat() if po.received_at else None,
            "created_at": po.created_at.isoformat()
        }
        results.append(po_data)

    return {
        "ok": True,
        "status": 200,
        "message": "Purchase Orders retrieved successfully",
        "data": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "purchase_orders": results
        }
    }

@router.get("/{po_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_purchase_order(
    po_id: UUID,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to view POs")

    po = db.query(TBL_PURCHASE_ORDER).filter(TBL_PURCHASE_ORDER.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    po_data = {
        "id": str(po.id),
        "po_number": po.po_number,
        "supplier_id": str(po.supplier_id),
        "supplier_name": po.supplier.name if po.supplier else "Unknown",
        "total_cost": float(po.total_cost),
        "status": po.status,
        "note": po.note,
        "ordered_at": po.ordered_at.isoformat() if po.ordered_at else None,
        "received_at": po.received_at.isoformat() if po.received_at else None,
        "created_at": po.created_at.isoformat(),
        "items": []
    }
    
    for item in po.items:
        po_data["items"].append({
            "id": str(item.id),
            "book_id": str(item.book_id),
            "book_title": item.book.title if item.book else "Unknown",
            "quantity": item.quantity,
            "cost_price": float(item.cost_price),
            "total_cost": float(item.total_cost)
        })

    return {
        "ok": True,
        "status": 200,
        "message": "PO retrieved successfully",
        "data": po_data
    }

@router.put("/{po_id}/status", response_model=dict, status_code=status.HTTP_200_OK)
def update_po_status(
    po_id: UUID,
    payload: PurchaseOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to update POs")

    po = db.query(TBL_PURCHASE_ORDER).filter(TBL_PURCHASE_ORDER.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
        
    if po.status == "received":
        raise HTTPException(status_code=400, detail="PO is already received and cannot be changed.")

    if payload.status == "received":
        # Business Logic: Increase Stock and Update Cost Price
        for item in po.items:
            book = item.book
            if book:
                # 1. Update Stock
                book.stock += item.quantity
                
                # 2. Update Cost Price to the latest PO price
                book.cost_price = item.cost_price
                
                # 2.5 Auto-Update Selling Price (Strict FIFO Batch Pricing)
                # ONLY update the retail price if this new PO is the ONLY active inventory we have
                if book.stock == item.quantity:
                    margin_multiplier = 1.0 + (float(book.min_profit_margin) / 100.0)
                    minimum_selling_price = float(item.cost_price) * margin_multiplier
                    if float(book.price) < minimum_selling_price:
                        book.price = minimum_selling_price
                
                # 3. Create Stock Batch
                batch = TBL_STOCK_BATCH(
                    book_id=book.id,
                    supplier_id=po.supplier_id,
                    po_item_id=item.id,
                    initial_quantity=item.quantity,
                    remaining_quantity=item.quantity,
                    unit_cost_price=item.cost_price,
                    status="active"
                )
                db.add(batch)
                
                # 4. Log Stock History
                stock_history = TBL_STOCK_HISTORY(
                    book_id=book.id,
                    quantity=item.quantity, # positive for stock IN
                    cost_price=item.cost_price,
                    sale_price=book.price,
                    user_id=current_user.id
                )
                db.add(stock_history)
                
                # 4. Log Inventory Transaction
                transaction = TBL_INVENTORY_TRANSACTION(
                    book_id=book.id,
                    transaction_type="purchase",
                    quantity=item.quantity,
                    current_stock=book.stock,
                    reference_id=str(po.id)
                )
                db.add(transaction)
                
        po.received_at = datetime.now()

    po.status = payload.status
    db.commit()

    return {
        "ok": True,
        "status": 200,
        "message": f"PO status updated to {payload.status}",
        "data": {"status": po.status}
    }
