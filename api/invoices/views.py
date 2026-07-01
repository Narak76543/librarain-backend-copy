import io
from fastapi import Query, Depends, status, HTTPException, Path
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from datetime import datetime, timezone, timedelta

from main import app
from core.db import get_db
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import get_current_user, require_admin

from api.invoices.models import TBL_INVOICE, TBL_INVOICE_ITEM
from api.invoices.services import create_invoice_for_order, generate_invoice_pdf, upload_pdf_to_cloudinary
from api.invoices.schemas import InvoiceResponse, InvoiceItemResponse, InvoiceListResponse

def serialize_invoice_item(item: TBL_INVOICE_ITEM) -> dict:
    return {
        "id"        : str(item.id),
        "book_id"   : str(item.book_id) if item.book_id else None,
        "book_title": item.book_title,
        "quantity"  : item.quantity,
        "unit_price": f"{item.unit_price:.2f}",
        "line_total": f"{item.line_total:.2f}",
        "profit"    : f"{item.profit:.2f}"
    }

def serialize_invoice(invoice: TBL_INVOICE) -> dict:
    return {
        "id"              : str(invoice.id),
        "invoice_number"  : invoice.invoice_number,
        "order_id"        : str(invoice.order_id) if invoice.order_id else None,
        "user_id"         : str(invoice.user_id) if invoice.user_id else None,
        "customer_name"   : invoice.user.full_name if invoice.user else "Walk-in Customer",
        "customer_email"  : invoice.user.email if invoice.user else "—",
        "customer_phone"  : invoice.user.phone if (invoice.user and invoice.user.phone) else "—",
        "delivery_way"    : invoice.order.delivery_way if invoice.order else "Pick Up",
        "delivery_partner": invoice.order.delivery_partner if (invoice.order and invoice.order.delivery_partner) else "—",
        "delivery_address": invoice.order.delivery_address if (invoice.order and invoice.order.delivery_address) else "—",
        "payment_method"  : invoice.order.payment_method if invoice.order else "COD",
        "subtotal"        : f"{invoice.subtotal:.2f}",
        "tax_amount"      : f"{invoice.tax_amount:.2f}",
        "discount_amount" : f"{invoice.discount_amount:.2f}",
        "delivery_fee"    : f"{invoice.delivery_fee:.2f}",
        "total"           : f"{invoice.total:.2f}",
        "status"          : invoice.status,
        "issued_at"       : invoice.issued_at.isoformat() if invoice.issued_at else None,
        "due_date"        : invoice.due_date.isoformat() if invoice.due_date else None,
        "paid_at"         : invoice.paid_at.isoformat() if invoice.paid_at else None,
        "pdf_url"         : invoice.pdf_url,
        "notes"           : invoice.notes,
        "items"           : [serialize_invoice_item(item) for item in invoice.items]
    }

# ==================== ADMIN ENDPOINTS ====================

@app.get("/api/v1/admin/invoices", tags=["Admin Invoices"])
def get_admin_invoices(
    page          : int           = Query(1, ge=1),
    limit         : int           = Query(10, ge=1, le=100),
    status        : str | None    = Query(None),
    customer      : str | None    = Query(None),
    invoice_number: str | None    = Query(None),
    order_id      : str | None    = Query(None),
    date_from     : str | None    = Query(None),
    date_to       : str | None    = Query(None),
    current_user  : TBL_AUTH_USER = Depends(require_admin),
    db            : Session       = Depends(get_db)
):
    offset = (page - 1) * limit
    query = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    )

    # Filters
    if order_id:
        query = query.filter(TBL_INVOICE.order_id == order_id)
    if status:
        query = query.filter(func.lower(TBL_INVOICE.status) == status.lower())
    if invoice_number:
        query = query.filter(TBL_INVOICE.invoice_number.ilike(f"%{invoice_number}%"))
    if customer:
        query = query.join(TBL_AUTH_USER, TBL_INVOICE.user_id == TBL_AUTH_USER.id).filter(
            or_(
                TBL_AUTH_USER.full_name.ilike(f"%{customer}%"),
                TBL_AUTH_USER.email.ilike(f"%{customer}%")
            )
        )
    if date_from:
        try:
            df    = datetime.strptime(date_from, "%Y-%m-%d")
            query = query.filter(TBL_INVOICE.issued_at >= df)
        except ValueError:
            pass
    if date_to:
        try:
            dt    = datetime.strptime(date_to, "%Y-%m-%d") + timedelta(days=1)
            query = query.filter(TBL_INVOICE.issued_at < dt)
        except ValueError:
            pass

    total = query.count()
    invoices = query.order_by(TBL_INVOICE.created_at.desc()).offset(offset).limit(limit).all()

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoices retrieved successfully",
        data        = {
            "total"   : total,
            "limit"   : limit,
            "offset"  : offset,
            "invoices": [serialize_invoice(inv) for inv in invoices]
        }
    )

@app.get("/api/v1/admin/invoices/{id}", tags=["Admin Invoices"])
def get_admin_invoice_detail(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.id == id).first()

    if not invoice:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Invoice not found"
        )

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoice retrieved successfully",
        data        = serialize_invoice(invoice)
    )

@app.get("/api/v1/admin/invoices/{id}/pdf", tags=["Admin Invoices"])
def get_admin_invoice_pdf(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.id == id).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_bytes = generate_invoice_pdf(invoice)
    filename  = f"invoice_{invoice.invoice_number}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@app.post("/api/v1/admin/invoices/{id}/regenerate", tags=["Admin Invoices"])
def regenerate_admin_invoice(
    id: str = Path(...),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db: Session = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.id == id).first()
    
    if not invoice:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Invoice not found"
        )

    try:
        pdf_bytes       = generate_invoice_pdf(invoice)
        pdf_url         = upload_pdf_to_cloudinary(pdf_bytes, invoice.invoice_number)
        invoice.pdf_url = pdf_url
        db.commit()
        db.refresh(invoice)
    except Exception as e:
        return response(
            ok          = False,
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR,
            message     = f"Failed to regenerate PDF: {str(e)}"
        )

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoice PDF regenerated successfully",
        data        = serialize_invoice(invoice)
    )

@app.put("/api/v1/admin/invoices/{id}/mark-paid", tags=["Admin Invoices"])
def mark_invoice_paid(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.id == id).first()
    
    if not invoice:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Invoice not found"
        )

    invoice.status  = "paid"
    invoice.paid_at = datetime.now(timezone.utc)

    # =========== Regenerate PDF to show updated status ===============
    try:
        pdf_bytes       = generate_invoice_pdf(invoice)
        pdf_url         = upload_pdf_to_cloudinary(pdf_bytes, invoice.invoice_number)
        invoice.pdf_url = pdf_url
    except Exception as e:
        print(f"Failed to upload regenerated invoice to Cloudinary: {e}")

    db.commit()
    db.refresh(invoice)

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoice marked as paid",
        data        = serialize_invoice(invoice)
    )

@app.put("/api/v1/admin/invoices/{id}/cancel", tags=["Admin Invoices"])
def cancel_invoice(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.id == id).first()
    
    if not invoice:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Invoice not found"
        )

    if invoice.status.lower() == "paid":
        return response(
            ok          = False,
            status_code = status.HTTP_400_BAD_REQUEST,
            message     = "Cannot cancel a paid invoice"
        )

    invoice.status = "cancelled"

    # Regenerate PDF to show updated status
    try:
        pdf_bytes       = generate_invoice_pdf(invoice)
        pdf_url         = upload_pdf_to_cloudinary(pdf_bytes, invoice.invoice_number)
        invoice.pdf_url = pdf_url
    except Exception as e:
        print(f"Failed to upload regenerated invoice to Cloudinary: {e}")

    db.commit()
    db.refresh(invoice)

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoice cancelled successfully",
        data        = serialize_invoice(invoice)
    )


# ==================== CUSTOMER ENDPOINTS ====================

@app.get("/api/v1/customer/invoices", tags=["Customer Invoices"])
def get_customer_invoices(
    page        : int           = Query(1, ge=1),
    limit       : int           = Query(10, ge=1, le=100),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db)
):
    offset = (page - 1) * limit
    query = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(TBL_INVOICE.user_id == current_user.id)

    total    = query.count()
    invoices = query.order_by(TBL_INVOICE.created_at.desc()).offset(offset).limit(limit).all()

    return response(
        ok          = True,
        status_code = 200,
        message     = "Customer invoices retrieved successfully",
        data        = {
            "total"   : total,
            "limit"   : limit,
            "offset"  : offset,
            "invoices": [serialize_invoice(inv) for inv in invoices]
        }
    )

@app.get("/api/v1/customer/invoices/{id}", tags=["Customer Invoices"])
def get_customer_invoice_detail(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(
        TBL_INVOICE.id == id,
        TBL_INVOICE.user_id == current_user.id
    ).first()

    if not invoice:
        return response(
            ok          = False,
            status_code = status.HTTP_404_NOT_FOUND,
            message     = "Invoice not found"
        )

    return response(
        ok          = True,
        status_code = 200,
        message     = "Invoice retrieved successfully",
        data        = serialize_invoice(invoice)
    )

@app.get("/api/v1/customer/invoices/{id}/download", tags=["Customer Invoices"])
def download_customer_invoice_pdf(
    id          : str           = Path(...),
    current_user: TBL_AUTH_USER = Depends(get_current_user),
    db          : Session       = Depends(get_db)
):
    invoice = db.query(TBL_INVOICE).options(
        joinedload(TBL_INVOICE.user),
        joinedload(TBL_INVOICE.items),
        joinedload(TBL_INVOICE.order)
    ).filter(
        TBL_INVOICE.id == id,
        TBL_INVOICE.user_id == current_user.id
    ).first()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    pdf_bytes = generate_invoice_pdf(invoice)
    filename  = f"invoice_{invoice.invoice_number}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type = "application/pdf",
        headers    = {"Content-Disposition": f"attachment; filename={filename}"}
    )
