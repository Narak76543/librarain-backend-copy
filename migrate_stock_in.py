from core.db import Session
from sqlalchemy import text

db = Session()
try:
    # Check existing stock in
    result = db.execute(text("SELECT COUNT(*) FROM tbl_stock_in")).scalar()
    if result > 0:
        print(f"TBL_STOCK_IN already has {result} records.")
        # We can still migrate, but let's see. Maybe the user added stock via web but it didn't save?
    
    # Let's just migrate all missing records using raw SQL
    # We will insert any record from tbl_stock_history that does not have a matching id in tbl_stock_in
    query = """
    INSERT INTO tbl_stock_in (id, book_id, quantity, cost_price, total_cost, note, created_by, created_at)
    SELECT h.id, h.book_id, h.quantity, h.cost_price, (h.quantity * h.cost_price), '', h.user_id, h.created_at
    FROM tbl_stock_history h
    WHERE NOT EXISTS (
        SELECT 1 FROM tbl_stock_in i WHERE i.id = h.id
    )
    """
    res = db.execute(text(query))
    db.commit()
    print(f"Migrated {res.rowcount} missing legacy records from tbl_stock_history to tbl_stock_in.")
    
except Exception as e:
    db.rollback()
    import traceback
    traceback.print_exc()
finally:
    db.close()
