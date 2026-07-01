import sys
import os
import uuid
from decimal import Decimal
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import configs
from api.books.models import TBL_BOOK
from api.inventory.models import TBL_STOCK_BATCH
from api.suppliers.models import TBL_SUPPLIER
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM, TBL_ORDER_ITEM_BATCH_ALLOCATION
from api.auth_user.models import TBL_AUTH_USER
from api.categories.models import TBL_CATEGORY
from api.user_profile.models import TBL_USER_PROFILE
from api.books.models import TBL_STOCK_HISTORY, TBL_STOCK_IN
from api.purchase_orders.models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM
from core.db import Base

def test_fifo():
    engine = create_engine(configs.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    db = Session()

    try:
        # Create a test supplier
        supplier1 = TBL_SUPPLIER(name="Supplier A", email="a@example.com")
        supplier2 = TBL_SUPPLIER(name="Supplier B", email="b@example.com")
        db.add_all([supplier1, supplier2])
        
        # Create a test book
        book = TBL_BOOK(title="Atomic Habits", author="James Clear", price=Decimal("20.00"), stock=0, isbn=str(uuid.uuid4())[:20])
        db.add(book)
        
        # Create test user
        user = TBL_AUTH_USER(email=f"test_{uuid.uuid4()}@example.com", full_name="Test User", password_hash="pw")
        db.add(user)
        
        db.flush()

        # Batch 1: 50 copies @ 10.00
        batch1 = TBL_STOCK_BATCH(
            book_id=book.id,
            supplier_id=supplier1.id,
            initial_quantity=50,
            remaining_quantity=50,
            unit_cost_price=Decimal("10.00"),
            status="active"
        )
        # Batch 2: 30 copies @ 12.50
        batch2 = TBL_STOCK_BATCH(
            book_id=book.id,
            supplier_id=supplier2.id,
            initial_quantity=30,
            remaining_quantity=30,
            unit_cost_price=Decimal("12.50"),
            status="active"
        )
        db.add_all([batch1, batch2])
        
        book.stock = 80
        db.flush()

        # Place an order for 60 copies
        order = TBL_ORDER(user_id=user.id, total=Decimal("1200.00"), status="pending")
        db.add(order)
        db.flush()
        
        order_item = TBL_ORDER_ITEM(
            order_id=order.id,
            book_id=book.id,
            quantity=60,
            price_at_purchase=Decimal("20.00")
        )
        db.add(order_item)
        db.commit()

        # Simulate update_order_status to delivered
        # (Copying the logic from views.py for testing)
        qty_to_fulfill = order_item.quantity
        total_cost = Decimal("0.00")
        
        batches = db.query(TBL_STOCK_BATCH).filter(
            TBL_STOCK_BATCH.book_id == book.id,
            TBL_STOCK_BATCH.remaining_quantity > 0
        ).order_by(TBL_STOCK_BATCH.received_at.asc()).all()
        
        for batch in batches:
            if qty_to_fulfill <= 0:
                break
            
            take_qty = min(batch.remaining_quantity, qty_to_fulfill)
            batch.remaining_quantity -= take_qty
            qty_to_fulfill -= take_qty
            
            if batch.remaining_quantity == 0:
                batch.status = "depleted"
                
            batch_cost = Decimal(str(take_qty)) * Decimal(str(batch.unit_cost_price))
            total_cost += batch_cost
            
            allocation = TBL_ORDER_ITEM_BATCH_ALLOCATION(
                order_item_id=order_item.id,
                stock_batch_id=batch.id,
                quantity_allocated=take_qty,
                unit_cost_price=batch.unit_cost_price
            )
            db.add(allocation)

        order_item.cost_price_at_purchase = total_cost / Decimal(str(order_item.quantity))
        book.stock = max(0, book.stock - order_item.quantity)
        
        db.commit()
        
        # Verify
        print(f"Total cost calculated: {total_cost} (Expected: 50*10 + 10*12.50 = 625)")
        print(f"Order item cost_price_at_purchase: {order_item.cost_price_at_purchase}")
        print(f"Batch 1 remaining: {batch1.remaining_quantity} (Expected: 0)")
        print(f"Batch 2 remaining: {batch2.remaining_quantity} (Expected: 20)")
        print(f"Book remaining stock: {book.stock} (Expected: 20)")

        # Cleanup
        db.query(TBL_ORDER_ITEM_BATCH_ALLOCATION).filter(TBL_ORDER_ITEM_BATCH_ALLOCATION.order_item_id == order_item.id).delete()
        db.delete(order_item)
        db.delete(order)
        db.delete(batch1)
        db.delete(batch2)
        db.delete(book)
        db.delete(supplier1)
        db.delete(supplier2)
        db.delete(user)
        db.commit()

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    test_fifo()
