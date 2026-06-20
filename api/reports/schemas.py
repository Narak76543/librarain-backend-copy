from pydantic import BaseModel
from typing import List

class StockInItem(BaseModel):
    title     : str
    category  : str
    qty_added : int
    cost_price: float
    total_cost: float

class StockInSummary(BaseModel):
    total_books_added: int
    total_qty        : int
    total_spent      : float

class StockInReport(BaseModel):
    items: List[StockInItem]
    summary: StockInSummary

class StockOutItem(BaseModel):
    title     : str
    qty_sold  : int
    sale_price: float
    revenue   : float
    delivery  : str
    payment   : str
    profit    : float

class StockOutSummary(BaseModel):
    total_orders  : int
    total_qty_sold: int
    total_revenue : float
    total_profit  : float

class StockOutReport(BaseModel):
    items: List[StockOutItem]
    summary: StockOutSummary

class DailySummary(BaseModel):
    revenue_today: float
    cost_today   : float
    net_profit   : float
    by_delivery  : int
    by_pick_up   : int
    paid_by_cod  : int
    paid_by_khqr : int

class DailyReportResponse(BaseModel):
    stock_in     : StockInReport
    stock_out    : StockOutReport
    daily_summary: DailySummary
