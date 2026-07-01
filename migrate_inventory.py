from core.db import engine, Base
from sqlalchemy import text
from api.inventory.models import TBL_STOCK_ADJUSTMENT
from api.books.models import TBL_BOOK
from api.auth_user.models import TBL_AUTH_USER

with engine.connect() as conn:
    try:
        conn.execute(text("ALTER TABLE tbl_book ADD COLUMN min_stock_level INTEGER NOT NULL DEFAULT 5;"))
        conn.commit()
        print("Added min_stock_level to tbl_book")
    except Exception as e:
        print(f"Failed to add column (might already exist): {e}")

Base.metadata.create_all(bind=engine)
print("Created TBL_STOCK_ADJUSTMENT table")
