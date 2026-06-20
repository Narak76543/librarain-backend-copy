from core.db import Session
from api.books.models import *
from api.categories.models import *
from api.auth_user.models import *
from api.orders.models import *

db = Session()
try:
    history = db.query(TBL_STOCK_IN).all()
    print("History length:", len(history))
    for h in history:
        print(f"Book: {h.book.title if h.book else 'No Book'}")
        print(f"User: {h.user.full_name if h.user else 'No User'}")
except Exception as e:
    import traceback
    traceback.print_exc()
finally:
    db.close()
