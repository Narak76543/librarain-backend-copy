import sys
import os
import uuid
from decimal import Decimal
from passlib.context import CryptContext

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.db import Base, engine, get_db
from sqlalchemy.orm import sessionmaker
from config import configs
from api.auth_user.models import TBL_AUTH_USER, TBL_AUTH_ROLE, TBL_AUTH_USER_ROLE
from api.suppliers.models import TBL_SUPPLIER
from api.books.models import TBL_BOOK, TBL_STOCK_HISTORY, TBL_STOCK_IN
from api.categories.models import TBL_CATEGORY
from api.user_profile.models import TBL_USER_PROFILE
from api.inventory.models import TBL_STOCK_BATCH, TBL_INVENTORY_TRANSACTION
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM, TBL_ORDER_ITEM_BATCH_ALLOCATION
from api.purchase_orders.models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM
from api.cart.models import TBL_CART_ITEM

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
db = SessionLocal()

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password)

# Cleanup previous test data safely
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

print("Seeding database...")

# Setup Admin User
admin_user = TBL_AUTH_USER(
    email="admin@example.com", 
    full_name="Admin User", 
    password_hash=hash_password("password"), 
    is_active=True
)
db.add(admin_user)
db.flush()

admin_role = TBL_AUTH_ROLE(role_code="ADMIN", role_name="Admin")
db.add(admin_role)
db.flush()

db.add(TBL_AUTH_USER_ROLE(user_id=admin_user.id, role_id=admin_role.id))
db.commit()
print("Created Admin User: admin@example.com / password")

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

# 2. Create Suppliers
sup_a = TBL_SUPPLIER(name="Supplier A", email="a@example.com")
sup_b = TBL_SUPPLIER(name="Supplier B", email="b@example.com")
db.add_all([sup_a, sup_b])
db.commit()

print("Data seeded successfully!")
