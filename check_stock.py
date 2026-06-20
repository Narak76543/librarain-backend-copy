from core.db import Session
from api.books.models import *
from api.categories.models import *
from api.auth_user.models import *
from api.orders.models import *

db = Session()
try:
    print("TBL_STOCK_IN count:", db.query(TBL_STOCK_IN).count())
    print("TBL_STOCK_HISTORY count:", db.query(TBL_STOCK_HISTORY).count())
    
    recent_in = db.query(TBL_STOCK_IN).order_by(TBL_STOCK_IN.created_at.desc()).limit(5).all()
    print("\nRecent TBL_STOCK_IN:")
    for h in recent_in:
        print(f"ID: {h.id}, Book: {h.book_id}, Qty: {h.quantity}, Created: {h.created_at}")

except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
