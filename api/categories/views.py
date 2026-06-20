import logging
from fastapi import Depends
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from starlette import status

from core.db import get_db
from main import app
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user, require_admin
from api.categories.models import TBL_CATEGORY
from api.categories import schemas

logger = logging.getLogger(__name__)


# ================= GET /categories ==========================
@app.get("/api/v1/categories", tags=["Categories"])
def get_categories(db: Session = Depends(get_db)):
    categories = (
        db.query(TBL_CATEGORY)
        .filter(TBL_CATEGORY.is_active.is_(True))
        .order_by(TBL_CATEGORY.name)
        .all()
    )

    data = jsonable_encoder([
        schemas.CategoryResponse.model_validate(c)
        for c in categories
    ])

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Categories retrieved successfully",
        data        = data,
    )


# ================= GET /categories/{id} =====================
@app.get("/api/v1/categories/{category_id}", tags=["Categories"])
def get_category(
    category_id: str,
    db         : Session = Depends(get_db),
):
    category = (
        db.query(TBL_CATEGORY)
        .filter(
            TBL_CATEGORY.id       == category_id,
            TBL_CATEGORY.is_active.is_(True),
        )
        .first()
    )

    if not category:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Category not found",
        )

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Category retrieved successfully",
        data        = jsonable_encoder(
            schemas.CategoryResponse.model_validate(category)
        ),
    )


# ================= POST /categories =========================
@app.post("/api/v1/categories", tags=["Categories"])
def create_category(
    payload     : schemas.CategoryCreate,
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    existing = (
        db.query(TBL_CATEGORY)
        .filter(TBL_CATEGORY.slug == payload.slug)
        .first()
    )

    if existing:
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Category with this slug already exists",
        )

    category = TBL_CATEGORY(**payload.model_dump())
    db.add(category)
    db.commit()
    db.refresh(category)

    return response(
        ok          = True,
        status_code = status.HTTP_201_CREATED,
        message     = "Category created successfully",
        data        = jsonable_encoder(
            schemas.CategoryResponse.model_validate(category)
        ),
    )


# ================= PUT /categories/{id} =====================
@app.put("/api/v1/categories/{category_id}", tags=["Categories"])
def update_category(
    category_id : str,
    payload     : schemas.CategoryUpdate,
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    category = (
        db.query(TBL_CATEGORY)
        .filter(TBL_CATEGORY.id == category_id)
        .first()
    )

    if not category:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Category not found",
        )

    if payload.slug:
        conflict = (
            db.query(TBL_CATEGORY)
            .filter(
                TBL_CATEGORY.slug == payload.slug,
                TBL_CATEGORY.id   != category_id,
            )
            .first()
        )
        if conflict:
            return response(
                ok          = False,
                status_code = status.HTTP_400_BAD_REQUEST,
                message     = "Another category with this slug already exists",
            )

    update_data = payload.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Category updated successfully",
        data        = jsonable_encoder(
            schemas.CategoryResponse.model_validate(category)
        ),
    )


# ================= DELETE /categories/{id} ==================
@app.delete("/api/v1/categories/{category_id}", tags=["Categories"])
def delete_category(
    category_id : str,
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db),
):
    category = (
        db.query(TBL_CATEGORY)
        .filter(TBL_CATEGORY.id == category_id)
        .first()
    )

    if not category:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Category not found",
        )

    category.is_active = False
    db.commit()

    return response(
        ok          = True,
        status_code = status.HTTP_200_OK,
        message     = "Category deleted successfully",
    )