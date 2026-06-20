from core.db import Session
from api.reports.views import fetch_daily_report_data
from datetime import date
from api.books.models import *
from api.categories.models import *
from api.orders.models import *
from api.auth_user.models import *

def test_daily():
    db = Session()
    try:
        report_date = date.today()
        data = fetch_daily_report_data(report_date, db)
        print("Stock In Items count:", len(data.stock_in.items))
        for item in data.stock_in.items:
            print("Stock in:", item.title, item.qty_added)
    finally:
        db.close()

if __name__ == '__main__':
    test_daily()
