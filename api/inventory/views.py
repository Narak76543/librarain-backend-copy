from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from typing import Any

from core.db import get_db
from api.auth_user.security import get_current_user
from api.auth_user.models import TBL_AUTH_USER
from api.books.models import TBL_BOOK
from api.inventory.models import TBL_STOCK_ADJUSTMENT, TBL_INVENTORY_TRANSACTION, TBL_STOCK_BATCH
from api.inventory.schemas import StockAdjustmentCreate, StockAdjustmentResponse

router = APIRouter(prefix="/api/v1/inventory", tags=["inventory"])

@router.get("/dashboard", response_model=dict, status_code=status.HTTP_200_OK)
def get_inventory_dashboard(
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    total_items = db.query(func.sum(TBL_BOOK.stock)).scalar() or 0
    total_value = db.query(func.sum(TBL_STOCK_BATCH.remaining_quantity * TBL_STOCK_BATCH.unit_cost_price)).filter(TBL_STOCK_BATCH.remaining_quantity > 0).scalar() or 0

    # Low stock logic
    low_stock_count = db.query(TBL_BOOK).filter(TBL_BOOK.stock <= TBL_BOOK.min_stock_level, TBL_BOOK.stock > 0).count()
    out_of_stock_count = db.query(TBL_BOOK).filter(TBL_BOOK.stock <= 0).count()

    return {
        "ok": True,
        "data": {
            "total_items": total_items,
            "total_value": float(total_value),
            "low_stock_count": low_stock_count,
            "out_of_stock_count": out_of_stock_count
        }
    }

@router.get("/{book_id}/batches", response_model=dict, status_code=status.HTTP_200_OK)
def get_book_batches(
    book_id: str,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")
        
    batches = db.query(TBL_STOCK_BATCH).filter(
        TBL_STOCK_BATCH.book_id == book_id,
        TBL_STOCK_BATCH.status == "active",
        TBL_STOCK_BATCH.remaining_quantity > 0
    ).order_by(TBL_STOCK_BATCH.received_at.asc()).all()
    
    return {
        "ok": True,
        "data": [
            {
                "id": str(b.id),
                "initial_quantity": b.initial_quantity,
                "remaining_quantity": b.remaining_quantity,
                "unit_cost_price": float(b.unit_cost_price),
                "received_at": b.received_at.isoformat()
            } for b in batches
        ]
    }

@router.get("/low-stock", response_model=dict, status_code=status.HTTP_200_OK)
def get_low_stock_books(
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    books = db.query(TBL_BOOK).filter(TBL_BOOK.stock <= TBL_BOOK.min_stock_level).order_by(TBL_BOOK.stock.asc()).all()
    
    return {
        "ok": True,
        "data": {
            "books": [
                {
                    "id": b.id,
                    "title": b.title,
                    "stock": b.stock,
                    "min_stock_level": b.min_stock_level,
                    "cover_url": b.cover_url
                }
                for b in books
            ]
        }
    }

@router.post("/adjust", response_model=dict, status_code=status.HTTP_201_CREATED)
def adjust_stock(
    payload: StockAdjustmentCreate,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    book = db.query(TBL_BOOK).filter(TBL_BOOK.id == payload.book_id).first()
    if not book:
        raise HTTPException(status_code=404, detail="Book not found")

    new_stock = book.stock + payload.quantity_adjusted
    if new_stock < 0:
        raise HTTPException(status_code=400, detail=f"Stock cannot be negative. Current stock is {book.stock}")

    adjustment = TBL_STOCK_ADJUSTMENT(
        book_id=payload.book_id,
        quantity_adjusted=payload.quantity_adjusted,
        reason=payload.reason,
        notes=payload.notes,
        created_by=current_user.id
    )
    
    book.stock = new_stock
    
    db.add(adjustment)
    db.flush()
    
    transaction = TBL_INVENTORY_TRANSACTION(
        book_id=book.id,
        transaction_type="adjustment",
        quantity=payload.quantity_adjusted,
        current_stock=book.stock,
        reference_id=str(adjustment.id)
    )
    db.add(transaction)
    
    db.commit()
    db.refresh(adjustment)

    return {
        "ok": True,
        "message": "Stock adjusted successfully",
        "data": {
            "book_id": str(book.id),
            "new_stock": book.stock,
            "adjustment_id": str(adjustment.id)
        }
    }

@router.get("/adjustments", response_model=dict, status_code=status.HTTP_200_OK)
def list_adjustments(
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    adjustments = db.query(TBL_STOCK_ADJUSTMENT).options(
        joinedload(TBL_STOCK_ADJUSTMENT.book),
        joinedload(TBL_STOCK_ADJUSTMENT.user)
    ).order_by(TBL_STOCK_ADJUSTMENT.created_at.desc()).all()

    return {
        "ok": True,
        "data": {
            "adjustments": [
                {
                    "id": a.id,
                    "book_title": a.book.title if a.book else "Unknown",
                    "quantity_adjusted": a.quantity_adjusted,
                    "reason": a.reason,
                    "notes": a.notes,
                    "created_by_name": a.user.full_name if a.user else "System",
                    "created_at": a.created_at
                }
                for a in adjustments
            ]
        }
    }


@router.get("/movements", response_model=dict, status_code=status.HTTP_200_OK)
def list_movements(
    book_id: str = None,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized")

    query = db.query(TBL_INVENTORY_TRANSACTION).options(
        joinedload(TBL_INVENTORY_TRANSACTION.book)
    )
    if book_id:
        query = query.filter(TBL_INVENTORY_TRANSACTION.book_id == book_id)
        
    movements = query.order_by(TBL_INVENTORY_TRANSACTION.created_at.desc()).all()

    return {
        "ok": True,
        "data": {
            "movements": [
                {
                    "id": str(m.id),
                    "book_id": str(m.book_id),
                    "book_title": m.book.title if m.book else "Unknown",
                    "transaction_type": m.transaction_type,
                    "quantity": m.quantity,
                    "current_stock": m.current_stock,
                    "reference_id": m.reference_id,
                    "created_at": m.created_at
                }
                for m in movements
            ]
        }
    }
