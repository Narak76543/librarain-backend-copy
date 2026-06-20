from fastapi import Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import date
from starlette import status
from main import app
from core.db import get_db
from api.auth_user.views import response
from api.auth_user.models import TBL_AUTH_USER
from api.auth_user.security import require_admin
from .schemas import DailyReportResponse, StockInReport, StockInItem, StockInSummary, StockOutReport, StockOutItem, StockOutSummary, DailySummary
from api.books.models import TBL_STOCK_IN, TBL_BOOK
from api.categories.models import TBL_CATEGORY
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM
import io
from fastapi.responses import StreamingResponse
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def fetch_daily_report_data(report_date: date, db: Session):
    if not report_date:
        report_date = date.today()

    # ====== STOCK IN ======
    stock_ins = db.query(TBL_STOCK_IN, TBL_BOOK, TBL_CATEGORY)\
        .join(TBL_BOOK, TBL_STOCK_IN.book_id == TBL_BOOK.id)\
        .outerjoin(TBL_CATEGORY, TBL_BOOK.category_id == TBL_CATEGORY.id)\
        .filter(func.date(TBL_STOCK_IN.created_at) == report_date)\
        .all()
    
    stock_in_items  = []
    total_qty_added = 0
    total_spent     = 0.0

    for si, book, category in stock_ins:
        category_name = category.name if category else "Uncategorized"
        stock_in_items.append(StockInItem(
            title      = book.title,
            category   = category_name,
            qty_added  = si.quantity,
            cost_price = float(si.cost_price),
            total_cost = float(si.total_cost)
        ))
        total_qty_added += si.quantity
        total_spent += float(si.total_cost)

    # ====== SECTION 2: STOCK OUT ======
    stock_outs = db.query(TBL_ORDER, TBL_ORDER_ITEM, TBL_BOOK)\
        .join(TBL_ORDER_ITEM, TBL_ORDER.id == TBL_ORDER_ITEM.order_id)\
        .join(TBL_BOOK, TBL_ORDER_ITEM.book_id == TBL_BOOK.id)\
        .filter(func.date(TBL_ORDER.created_at) == report_date)\
        .all()

    stock_out_items = []
    unique_orders   = set()
    total_qty_sold  = 0
    total_revenue   = 0.0
    total_profit    = 0.0

    by_delivery  = 0
    by_pick_up   = 0
    paid_by_cod  = 0
    paid_by_khqr = 0

    orders_processed = set()

    for order, item, book in stock_outs:
        unique_orders.add(order.id)
        revenue = float(item.price_at_purchase) * item.quantity
        profit  = (float(item.price_at_purchase) - float(item.cost_price_at_purchase)) * item.quantity
        
        stock_out_items.append(StockOutItem(
            title      = book.title,
            qty_sold   = item.quantity,
            sale_price = float(item.price_at_purchase),
            revenue    = revenue,
            delivery   = order.delivery_way or "Pick Up",
            payment    = order.payment_method or "COD",
            profit     = profit
        ))
        
        total_qty_sold += item.quantity
        total_revenue  += revenue
        total_profit   += profit

        if order.id not in orders_processed:
            orders_processed.add(order.id)
            if (order.delivery_way or "").lower() == "pick up":
                by_pick_up += 1
            else:
                by_delivery += 1
            
            if (order.payment_method or "COD").upper() == "COD":
                paid_by_cod += 1
            else:
                paid_by_khqr += 1

    cost_today = total_revenue - total_profit

    resp_data = DailyReportResponse(
        stock_in=StockInReport(
            items=stock_in_items,
            summary=StockInSummary(
                total_books_added = len({si.book_id for si, b, c in stock_ins}),
                total_qty         = total_qty_added,
                total_spent       = total_spent
            )
        ),
        stock_out=StockOutReport(
            items=stock_out_items,
            summary=StockOutSummary(
                total_orders   = len(unique_orders),
                total_qty_sold = total_qty_sold,
                total_revenue  = total_revenue,
                total_profit   = total_profit
            )
        ),
        daily_summary=DailySummary(
            revenue_today = total_revenue,
            cost_today    = cost_today,
            net_profit    = total_profit,
            by_delivery   = by_delivery,
            by_pick_up    = by_pick_up,
            paid_by_cod   = paid_by_cod,
            paid_by_khqr  = paid_by_khqr
        )
    )
    return resp_data

@app.get("/api/v1/admin/reports/daily", tags=["Reports"])
def get_daily_report(
    report_date: date = None,
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not report_date:
        report_date = date.today()
    resp_data = fetch_daily_report_data(report_date, db)
    return response(
        ok=True,
        status_code=status.HTTP_200_OK,
        message="Daily report retrieved",
        data=resp_data.model_dump()
    )

@app.get("/api/v1/admin/reports/daily/export", tags=["Reports"])
def export_daily_report_excel(
    report_date: date = None,
    current_user: TBL_AUTH_USER = Depends(require_admin),
    db: Session = Depends(get_db)
):
    if not report_date:
        report_date = date.today()
        
    data = fetch_daily_report_data(report_date, db)
    wb = openpyxl.Workbook()
    
    # Standard styles
    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", fgColor="333333")
    align_center = Alignment(horizontal="center", vertical="center")
    align_right = Alignment(horizontal="right", vertical="center")
    thin_border = Border(left=Side(style='thin'), right=Side(style='thin'), top=Side(style='thin'), bottom=Side(style='thin'))
    
    def apply_header_style(cell):
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = align_center
        cell.border = thin_border

    # === Sheet 1: Summary ===
    ws_summary = wb.active
    ws_summary.title = "Daily Summary"
    
    ws_summary.append(["Daily Report Summary", str(report_date)])
    ws_summary.append([])
    
    summary = data.daily_summary
    metrics = [
        ("Revenue Today", f"${summary.revenue_today:,.2f}"),
        ("Cost Today", f"${summary.cost_today:,.2f}"),
        ("Net Profit", f"${summary.net_profit:,.2f}"),
        ("By Delivery", str(summary.by_delivery)),
        ("By Pick Up", str(summary.by_pick_up)),
        ("Paid by COD", str(summary.paid_by_cod)),
        ("Paid by KHQR", str(summary.paid_by_khqr)),
    ]
    
    ws_summary.append(["Metric", "Value"])
    for cell in ws_summary[3]:
        apply_header_style(cell)
        
    for k, v in metrics:
        ws_summary.append([k, v])
        
    ws_summary.column_dimensions['A'].width = 20
    ws_summary.column_dimensions['B'].width = 15

    # === Sheet 2: Stock In ===
    ws_in = wb.create_sheet(title="Stock In")
    ws_in.append(["Book Title", "Category", "Qty Added", "Cost Price", "Total Cost"])
    for cell in ws_in[1]:
        apply_header_style(cell)
        
    for item in data.stock_in.items:
        row = [item.title, item.category, item.qty_added, item.cost_price, item.total_cost]
        ws_in.append(row)
        
    # Formatting
    for row in ws_in.iter_rows(min_row=2, max_col=5):
        row[3].number_format = '"$"#,##0.00'
        row[4].number_format = '"$"#,##0.00'
        
    ws_in.column_dimensions['A'].width = 30
    ws_in.column_dimensions['B'].width = 20
    ws_in.column_dimensions['C'].width = 12
    ws_in.column_dimensions['D'].width = 15
    ws_in.column_dimensions['E'].width = 15

    # === Sheet 3: Stock Out ===
    ws_out = wb.create_sheet(title="Stock Out")
    ws_out.append(["Book Title", "QTY Sold", "Sale Price", "Revenue", "Delivery", "Payment", "Profit"])
    for cell in ws_out[1]:
        apply_header_style(cell)
        
    for item in data.stock_out.items:
        row = [item.title, item.qty_sold, item.sale_price, item.revenue, item.delivery, item.payment, item.profit]
        ws_out.append(row)
        
    # Formatting
    for row in ws_out.iter_rows(min_row=2, max_col=7):
        row[2].number_format = '"$"#,##0.00'
        row[3].number_format = '"$"#,##0.00'
        row[6].number_format = '"$"#,##0.00'
        
    ws_out.column_dimensions['A'].width = 30
    ws_out.column_dimensions['B'].width = 12
    ws_out.column_dimensions['C'].width = 15
    ws_out.column_dimensions['D'].width = 15
    ws_out.column_dimensions['E'].width = 15
    ws_out.column_dimensions['F'].width = 15
    ws_out.column_dimensions['G'].width = 15

    # Save to bytes
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    headers = {
        'Content-Disposition': f'attachment; filename="Daily_Report_{report_date}.xlsx"'
    }
    
    return StreamingResponse(
        output,
        headers=headers,
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
