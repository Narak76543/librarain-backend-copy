import urllib.request
import urllib.parse
import json
import traceback
from core.db import Session
from api.books.models import *
from api.auth_user.models import *
from api.categories.models import *
from api.user_profile.models import *
from api.orders.models import *
from datetime import datetime, timezone, timedelta

def run_test():
    db = Session()
    try:
        now = datetime.now(timezone.utc)
        start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        end   = now
        
        print("Start:", start)
        print("End:", end)
        
        query = (
            db.query(TBL_BOOK)
            .filter(TBL_BOOK.is_active.is_(True))
            .filter(TBL_BOOK.created_at >= start)
            .filter(TBL_BOOK.created_at <= end)
        )
        books = query.all()
        print(f"Found {len(books)} books created this month.")
        
        # Test serialization
        for b in books:
            cost_price  = float(b.cost_price or 0.0)
            sale_price  = float(b.price)
            stock_value = cost_price * b.stock
            print(f"Book: {b.title}, Created At: {b.created_at}")

        # KPI logic
        stock_history = db.query(TBL_STOCK_HISTORY).all()
        print(f"Found {len(stock_history)} stock history records.")
        total_books_added = sum([h.quantity for h in stock_history])
        print(f"Total Books Added: {total_books_added}")

    except Exception as e:
        traceback.print_exc()
    finally:
        db.close()

if __name__ == '__main__':
    run_test()
