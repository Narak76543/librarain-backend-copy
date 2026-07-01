import io
import datetime
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM
from api.invoices.models import TBL_INVOICE, TBL_INVOICE_ITEM
from config import configs

import cloudinary
import cloudinary.uploader

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

def generate_invoice_number(db: Session, target_year: int) -> str:
    prefix = f"INV-{target_year}-"
    # Find the maximum invoice number for the target year
    max_invoice = db.query(TBL_INVOICE).filter(
        TBL_INVOICE.invoice_number.like(f"{prefix}%")
    ).order_by(TBL_INVOICE.invoice_number.desc()).first()

    if max_invoice:
        try:
            last_seq = int(max_invoice.invoice_number.split("-")[-1])
            new_seq = last_seq + 1
        except Exception:
            new_seq = 1
    else:
        new_seq = 1

    return f"{prefix}{new_seq:05d}"

def upload_pdf_to_cloudinary(pdf_bytes: bytes, invoice_number: str) -> str:
    cloudinary.config(
        cloud_name = configs.CLOUDINARY_CLOUD_NAME,
        api_key    = configs.CLOUDINARY_API_KEY,
        api_secret = configs.CLOUDINARY_API_SECRET,
    )
    result = cloudinary.uploader.upload(
        pdf_bytes,
        public_id=f"invoices/{invoice_number}.pdf",
        resource_type="raw",
    )
    return result.get("secure_url")

def generate_invoice_pdf(invoice: TBL_INVOICE) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
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

    # ===== Header ======== 
    header_style = ParagraphStyle(
        "header",
        fontSize  = 22,
        leading   = 26,
        textColor = GREEN,
        fontName  = "Helvetica-Bold",
        alignment = TA_LEFT,
    )
    sub_style = ParagraphStyle(
        "sub",
        fontSize  = 10,
        leading   = 14,
        textColor = GRAY,
        fontName  = "Helvetica",
        alignment = TA_LEFT,
    )
    right_style = ParagraphStyle(
        "right",
        fontSize  = 10,
        leading   = 14,
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

    #========= BookStore Info & Invoice Label =====================
    header_data = [
        [
            Paragraph("BookStore / Librarain", header_style),
            Paragraph(
                f"<b>INVOICE</b><br/>"
                f"Invoice #: {invoice.invoice_number}<br/>"
                f"Date: {invoice.issued_at.strftime('%b %d, %Y') if invoice.issued_at else ''}",
                right_style,
            ),
        ]
    ]
    header_table = Table(header_data, colWidths=[110*mm, 60*mm])
    header_table.setStyle(TableStyle([
        ("VALIGN",     (0,0), (-1,-1), "TOP"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    elements.append(header_table)
    elements.append(HRFlowable(width="100%", thickness=1, color=GREEN, spaceAfter=8))

    # ================== Customer Info ==========================================
    cust_email = invoice.user.email if invoice.user else "—"
    cust_name = invoice.user.full_name if invoice.user else "Walk-in Customer"
    cust_phone = invoice.user.phone if invoice.user and invoice.user.phone else "—"
    cust_address = "—"
    if invoice.order and invoice.order.delivery_address:
        cust_address = invoice.order.delivery_address

    elements.append(Paragraph("Bill To:", ParagraphStyle("label", fontSize=9, textColor=GRAY, fontName="Helvetica")))
    elements.append(Spacer(1, 2*mm))
    elements.append(Paragraph(cust_name, bold_style))
    elements.append(Paragraph(f"Email: {cust_email}", sub_style))
    elements.append(Paragraph(f"Phone: {cust_phone}", sub_style))
    elements.append(Paragraph(f"Address: {cust_address}", sub_style))
    elements.append(Spacer(1, 6*mm))

    # ================ Invoice details (Dates & Status) ==================================
    invoice_details_data = [
        ["Due Date:", invoice.due_date.strftime("%b %d, %Y") if invoice.due_date else "—"],
        ["Invoice Status:", invoice.status.upper()],
        ["Payment Method:", invoice.order.payment_method if invoice.order else "COD"],
    ]
    if invoice.order and invoice.order.delivery_way == "Delivery":
        invoice_details_data.append(["Delivery Method:", f"Delivery via {invoice.order.delivery_partner or 'Standard'}"])
    else:
        invoice_details_data.append(["Delivery Method:", "Pick Up"])

    details_table_data = []
    for k, v in invoice_details_data:
        details_table_data.append([
            Paragraph(f"<b>{k}</b>", ParagraphStyle("k", fontName="Helvetica-Bold", fontSize=9, textColor=DARK)),
            Paragraph(v, ParagraphStyle("v", fontName="Helvetica", fontSize=9, textColor=GRAY))
        ])

    details_table = Table(details_table_data, colWidths=[40*mm, 130*mm])
    details_table.setStyle(TableStyle([
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    elements.append(details_table)
    elements.append(Spacer(1, 6*mm))

    # ======================== Items table =================================
    elements.append(Paragraph("Invoice Items", bold_style))
    elements.append(Spacer(1, 3*mm))

    table_data  = [["#", "Book Title", "Qty", "Unit Price", "Subtotal"]]
    for i, item in enumerate(invoice.items, 1):
        table_data.append([
            str(i),
            item.book_title,
            str(item.quantity),
            f"${item.unit_price:.2f}",
            f"${item.line_total:.2f}",
        ])

    items_table = Table(
        table_data,
        colWidths = [10*mm, 95*mm, 15*mm, 25*mm, 25*mm],
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
        ("ALIGN",        (2,1), (-1,-1), "CENTER"),
        ("ALIGN",        (3,1), (-1,-1), "RIGHT"),
        ("ALIGN",        (4,1), (-1,-1), "RIGHT"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1), [colors.white, LIGHT]),
        ("TOPPADDING",   (0,1), (-1,-1), 5),
        ("BOTTOMPADDING",(0,1), (-1,-1), 5),
        # Grid
        ("GRID",         (0,0), (-1,-1), 0.5, colors.HexColor("#E5E7EB")),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 6*mm))

    # ======= Summary totals ========================
    summary_data = [
        ["", "Subtotal:",  f"${invoice.subtotal:.2f}"],
        ["", "Tax:",       f"${invoice.tax_amount:.2f}"],
        ["", "Discount:",  f"-${invoice.discount_amount:.2f}"],
        ["", "Delivery:",  f"${invoice.delivery_fee:.2f}"],
        ["", "TOTAL:",     f"${invoice.total:.2f}"],
    ]
    summary_table = Table(summary_data, colWidths=[110*mm, 35*mm, 25*mm])
    summary_table.setStyle(TableStyle([
        ("FONTNAME",     (0,0), (-1,-2), "Helvetica"),
        ("FONTNAME",     (1,4), (-1,4),  "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("TEXTCOLOR",    (1,0), (1,-2),  GRAY),
        ("TEXTCOLOR",    (2,0), (2,-2),  DARK),
        ("TEXTCOLOR",    (1,4), (-1,4),  GREEN),
        ("FONTSIZE",     (1,4), (-1,4),  12),
        ("ALIGN",        (1,0), (-1,-1), "RIGHT"),
        ("LINEABOVE",    (1,4), (-1,4),  1, GREEN),
        ("TOPPADDING",   (0,4), (-1,4),  6),
    ]))
    elements.append(summary_table)
    elements.append(Spacer(1, 8*mm))

    # =========== Footer ========================
    elements.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    elements.append(Spacer(1, 3*mm))
    elements.append(Paragraph(
        "Thank you for your purchase. 📚",
        ParagraphStyle("footer", fontSize=9, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER)
    ))
    elements.append(Paragraph(
        "For support contact: support@bookstore.com",
        ParagraphStyle("footer2", fontSize=8, textColor=GRAY, fontName="Helvetica", alignment=TA_CENTER)
    ))

    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    return pdf_data

def create_invoice_for_order(db: Session, order: TBL_ORDER) -> TBL_INVOICE:
    # ========= Check if invoice already exists for this order =============================
    existing_invoice = db.query(TBL_INVOICE).filter(TBL_INVOICE.order_id == order.id).first()
    if existing_invoice:
        return existing_invoice

    # ======== Calculate values =========================
    subtotal = sum(oi.price_at_purchase * oi.quantity for oi in order.order_items)
    delivery_fee = Decimal("0.00")
    discount_amount = Decimal("0.00")
    tax_amount = Decimal("0.00")
    total = subtotal + delivery_fee - discount_amount

    # ============= Map status: default is "issued", but if payment method is COD and order is just delivered (not completed), keep "issued". If completed or not COD, mark "paid".
    status = "issued"
    paid_at = None
    if order.status.lower() == "completed" or (order.payment_method and order.payment_method.upper() != "COD"):
        status = "paid"
        paid_at = datetime.datetime.now(datetime.timezone.utc)

    # ========== Generate invoice number =======================
    target_year = datetime.datetime.now().year
    invoice_number = generate_invoice_number(db, target_year)

    # 4. Create TBL_INVOICE record
    issued_at = datetime.datetime.now(datetime.timezone.utc)
    due_date = issued_at + datetime.timedelta(days=14)

    invoice = TBL_INVOICE(
        invoice_number  = invoice_number,
        order_id        = order.id,
        user_id         = order.user_id,
        subtotal        = subtotal,
        tax_amount      = tax_amount,
        discount_amount = discount_amount,
        delivery_fee    = delivery_fee,
        total           = total,
        status          = status,
        issued_at       = issued_at,
        due_date        = due_date,
        paid_at         = paid_at,
        pdf_url         = None,
        notes           = f"Auto-generated for Order #{str(order.id)[:8].upper()}"
    )
    db.add(invoice)
    db.flush()  # to get invoice.id

    # ============ Create TBL_INVOICE_ITEM records ======================
    for oi in order.order_items:
        cost_price = oi.cost_price_at_purchase or (oi.book.cost_price if oi.book else Decimal("0.00")) or oi.price_at_purchase * Decimal("0.6")
        line_total = oi.price_at_purchase * oi.quantity
        profit = (oi.price_at_purchase - cost_price) * oi.quantity
        
        invoice_item = TBL_INVOICE_ITEM(
            invoice_id = invoice.id,
            book_id    = oi.book_id,
            book_title = oi.book.title if oi.book else "Deleted book",
            quantity   = oi.quantity,
            unit_price = oi.price_at_purchase,
            cost_price = cost_price,
            line_total = line_total,
            profit     = profit
        )
        db.add(invoice_item)

    db.flush()
    # ================= Refresh to ensure relationships/items are loaded before PDF generation ======================
    db.refresh(invoice)

    # ========== Generate and upload PDF ========================
    try:
        pdf_bytes = generate_invoice_pdf(invoice)
        pdf_url = upload_pdf_to_cloudinary(pdf_bytes, invoice_number)
        invoice.pdf_url = pdf_url
    except Exception as e:
        # ================ Fallback to no PDF url on error (e.g. internet issues in tests) ==========================
        print(f"Cloudinary upload failed: {e}")
        invoice.pdf_url = None

    db.commit()
    db.refresh(invoice)
    return invoice
