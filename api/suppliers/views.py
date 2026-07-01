from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List, Any

from core.db import get_db
from api.auth_user.security import get_current_user
from api.auth_user.models import TBL_AUTH_USER
from .models import TBL_SUPPLIER
from .schemas import SupplierCreate, SupplierUpdate, SupplierResponse

router = APIRouter(prefix="/api/v1/suppliers", tags=["Suppliers"])

@router.post("", response_model=dict, status_code=status.HTTP_201_CREATED)
def create_supplier(
    payload: SupplierCreate,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to create suppliers")
    
    supplier = TBL_SUPPLIER(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    
    return {
        "ok": True,
        "status": 201,
        "message": "Supplier created successfully",
        "data": SupplierResponse.model_validate(supplier).model_dump()
    }

@router.get("", response_model=dict, status_code=status.HTTP_200_OK)
def list_suppliers(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to view suppliers")

    query = db.query(TBL_SUPPLIER)
    total = query.count()
    suppliers = query.order_by(TBL_SUPPLIER.created_at.desc()).offset(skip).limit(limit).all()

    return {
        "ok": True,
        "status": 200,
        "message": "Suppliers retrieved successfully",
        "data": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "suppliers": [SupplierResponse.model_validate(s).model_dump() for s in suppliers]
        }
    }

@router.get("/{supplier_id}", response_model=dict, status_code=status.HTTP_200_OK)
def get_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to view suppliers")

    supplier = db.query(TBL_SUPPLIER).filter(TBL_SUPPLIER.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return {
        "ok": True,
        "status": 200,
        "message": "Supplier retrieved successfully",
        "data": SupplierResponse.model_validate(supplier).model_dump()
    }

@router.put("/{supplier_id}", response_model=dict, status_code=status.HTTP_200_OK)
def update_supplier(
    supplier_id: UUID,
    payload: SupplierUpdate,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to update suppliers")

    supplier = db.query(TBL_SUPPLIER).filter(TBL_SUPPLIER.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(supplier, key, value)

    db.commit()
    db.refresh(supplier)

    return {
        "ok": True,
        "status": 200,
        "message": "Supplier updated successfully",
        "data": SupplierResponse.model_validate(supplier).model_dump()
    }

@router.delete("/{supplier_id}", response_model=dict, status_code=status.HTTP_200_OK)
def delete_supplier(
    supplier_id: UUID,
    db: Session = Depends(get_db),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
) -> Any:
    roles = [ur.role.role_code for ur in current_user.user_roles]
    if "ADMIN" not in roles:
        raise HTTPException(status_code=403, detail="Not authorized to delete suppliers")

    supplier = db.query(TBL_SUPPLIER).filter(TBL_SUPPLIER.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db.delete(supplier)
    db.commit()

    return {
        "ok": True,
        "status": 200,
        "message": "Supplier deleted successfully",
        "data": None
    }
