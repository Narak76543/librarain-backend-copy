import sys
import os

# Add the current directory to sys.path so we can import from core and api
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import main

from core.db import Session
from api.purchase_orders.models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM
from api.inventory.models import TBL_INVENTORY_TRANSACTION, TBL_STOCK_BATCH
from api.books.models import TBL_BOOK, TBL_STOCK_HISTORY

def delete_pos(po_numbers):
    db = Session()
    try:
        for po_num in po_numbers:
            po = db.query(TBL_PURCHASE_ORDER).filter(TBL_PURCHASE_ORDER.po_number == po_num).first()
            if not po:
                print(f"PO {po_num} not found.")
                continue

            print(f"Deleting {po_num} (ID: {po.id})...")

            # 1. Delete inventory transactions
            transactions = db.query(TBL_INVENTORY_TRANSACTION).filter(TBL_INVENTORY_TRANSACTION.reference_id == str(po.id)).all()
            for tx in transactions:
                db.delete(tx)
            
            # 2. Revert book stock and delete stock batches
            for item in po.items:
                book = item.book
                if book and po.status == "received":
                    # Revert stock
                    book.stock -= item.quantity
                    print(f"  Reverted stock for book {book.title} by {item.quantity}. New stock: {book.stock}")
                    
                    # Delete stock batch
                    batches = db.query(TBL_STOCK_BATCH).filter(TBL_STOCK_BATCH.po_item_id == item.id).all()
                    for b in batches:
                        db.delete(b)

                # Delete PO Item
                db.delete(item)

            # Delete PO itself
            db.delete(po)
            print(f"Successfully deleted {po_num}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    delete_pos(["PO-2026-00004", "PO-2026-00003"])
