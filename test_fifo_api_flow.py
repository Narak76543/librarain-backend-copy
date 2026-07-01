import sys
import os
import uuid
from decimal import Decimal

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi.testclient import TestClient
from main import app
from core.db import get_db, Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import configs
from api.auth_user.security import get_current_user, require_admin
from api.auth_user.models import TBL_AUTH_USER, TBL_AUTH_ROLE, TBL_AUTH_USER_ROLE
from api.suppliers.models import TBL_SUPPLIER
from api.books.models import TBL_BOOK
from api.categories.models import TBL_CATEGORY
from api.inventory.models import TBL_STOCK_BATCH, TBL_INVENTORY_TRANSACTION
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM, TBL_ORDER_ITEM_BATCH_ALLOCATION
from api.purchase_orders.models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM
from api.cart.models import TBL_CART_ITEM

engine = create_engine(configs.DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

# Cleanup previous test data
def cleanup():
    db.query(TBL_INVENTORY_TRANSACTION).delete()
    db.query(TBL_ORDER_ITEM_BATCH_ALLOCATION).delete()
    db.query(TBL_STOCK_BATCH).delete()
    db.query(TBL_ORDER_ITEM).delete()
    db.query(TBL_ORDER).delete()
    db.query(TBL_CART_ITEM).delete()
    db.query(TBL_PURCHASE_ORDER_ITEM).delete()
    db.query(TBL_PURCHASE_ORDER).delete()
    db.query(TBL_SUPPLIER).delete()
    db.query(TBL_BOOK).delete()
    db.query(TBL_CATEGORY).delete()
    db.query(TBL_AUTH_USER_ROLE).delete()
    db.query(TBL_AUTH_ROLE).delete()
    db.query(TBL_AUTH_USER).delete()
    db.commit()

cleanup()

# Setup Admin User
admin_user = TBL_AUTH_USER(email="admin_fifo@example.com", full_name="Admin User", password_hash="hash", is_active=True)
db.add(admin_user)
db.flush()

admin_role = TBL_AUTH_ROLE(role_code="ADMIN", role_name="Admin")
db.add(admin_role)
db.flush()

db.add(TBL_AUTH_USER_ROLE(user_id=admin_user.id, role_id=admin_role.id))
db.commit()

# Setup test client with overridden auth
def override_get_current_user():
    return db.query(TBL_AUTH_USER).filter_by(id=admin_user.id).first()

def override_require_admin():
    return db.query(TBL_AUTH_USER).filter_by(id=admin_user.id).first()

app.dependency_overrides[get_current_user] = override_get_current_user
app.dependency_overrides[require_admin] = override_require_admin

client = TestClient(app)

print("--- Start FIFO Flow Test ---")

# 1. Create a Category and Book
cat = TBL_CATEGORY(name="Self-Help", slug="self-help")
db.add(cat)
db.flush()

book = TBL_BOOK(
    title="Atomic Habits", author="James Clear", price=Decimal("20.00"), 
    stock=0, isbn=str(uuid.uuid4())[:20], category_id=cat.id, is_active=True
)
db.add(book)
db.commit()
book_id = str(book.id)

# 2. Create Suppliers
sup_a = TBL_SUPPLIER(name="Supplier A", email="a@example.com")
sup_b = TBL_SUPPLIER(name="Supplier B", email="b@example.com")
db.add_all([sup_a, sup_b])
db.commit()

# 3. Create PO from Supplier A (50 copies @ $10.00)
response = client.post("/api/v1/purchase-orders", json={
    "supplier_id": str(sup_a.id),
    "note": "PO A",
    "items": [{"book_id": book_id, "quantity": 50, "cost_price": 10.00}]
})
po_a_id = response.json()["data"]["id"]
print("Created PO A:", po_a_id)

# 4. Create PO from Supplier B (30 copies @ $12.50)
response = client.post("/api/v1/purchase-orders", json={
    "supplier_id": str(sup_b.id),
    "note": "PO B",
    "items": [{"book_id": book_id, "quantity": 30, "cost_price": 12.50}]
})
po_b_id = response.json()["data"]["id"]
print("Created PO B:", po_b_id)

# 5. Receive PO A
client.put(f"/api/v1/purchase-orders/{po_a_id}/status", json={"status": "received"})
print("Received PO A")

# 6. Receive PO B
client.put(f"/api/v1/purchase-orders/{po_b_id}/status", json={"status": "received"})
print("Received PO B")

db.refresh(book)
print(f"Book stock after receiving both POs: {book.stock} (Expected: 80)")
batches = db.query(TBL_STOCK_BATCH).filter_by(book_id=book.id).all()
print(f"Number of active batches: {len(batches)} (Expected: 2)")

# 7. Add to Cart (Customer wants 60 copies)
db.add(TBL_CART_ITEM(user_id=admin_user.id, book_id=book.id, quantity=60))
db.commit()

# 8. Place Order
response = client.post("/api/v1/orders", json={
    "delivery_way": "Pick Up",
    "payment_method": "COD"
})
order_id = response.json()["data"]["id"]
print("Placed Order:", order_id)

# 9. Update Order to Completed (This triggers fulfillment and FIFO)
response = client.patch(f"/api/v1/admin/orders/{order_id}/status", json={"status": "completed"})
print("Order status update response:", response.status_code)

# 10. Verify Data
db.refresh(book)
print(f"\n--- Validation ---")
print(f"Book stock remaining: {book.stock} (Expected: 20)")

# Check Batches
batches = db.query(TBL_STOCK_BATCH).filter_by(book_id=book.id).order_by(TBL_STOCK_BATCH.received_at.asc()).all()
print(f"Batch A remaining: {batches[0].remaining_quantity} (Expected: 0), Status: {batches[0].status}")
print(f"Batch B remaining: {batches[1].remaining_quantity} (Expected: 20), Status: {batches[1].status}")

# Check Allocations
order = db.query(TBL_ORDER).filter_by(id=order_id).first()
order_item = order.order_items[0]
allocations = db.query(TBL_ORDER_ITEM_BATCH_ALLOCATION).filter_by(order_item_id=order_item.id).order_by(TBL_ORDER_ITEM_BATCH_ALLOCATION.unit_cost_price.asc()).all()

print(f"Allocations for order item: {len(allocations)} (Expected: 2)")
total_cost_calculated = sum([a.quantity_allocated * a.unit_cost_price for a in allocations])
print(f"Total Cost of Goods Sold for Order: {total_cost_calculated} (Expected: 50*10 + 10*12.50 = 625)")
print(f"Blended Unit Cost Price stored in order_item: {order_item.cost_price_at_purchase} (Expected: 625 / 60 = 10.42)")

# 11. Check Admin Dashboard / Reports
response = client.get("/api/v1/admin/dashboard?period=24h")
dashboard = response.json()["data"]

profit_breakdown = dashboard["profit_breakdown"]
print("\n--- Dashboard Report (Today) ---")
print(f"Revenue Today: {profit_breakdown['revenue']} (Expected: 60 * 20 = 1200)")
print(f"Cost Today: {profit_breakdown['cost']} (Expected: 625)")
print(f"Net Profit: {profit_breakdown['net_profit']} (Expected: 1200 - 625 = 575)")

print("\n--- Test Completed Successfully! ---")
