import os
import importlib
from core.db import Base, engine
from sqlalchemy import inspect
from api.auth_user.models import TBL_AUTH_USER
from api.user_profile.models import TBL_USER_PROFILE
from api.categories.models import TBL_CATEGORY
from api.books.models import TBL_BOOK, TBL_STOCK_HISTORY, TBL_STOCK_IN
from api.cart.models import TBL_CART_ITEM
from api.orders.models import TBL_ORDER, TBL_ORDER_ITEM
from api.invoices.models import TBL_INVOICE
from api.suppliers.models import TBL_SUPPLIER
from api.purchase_orders.models import TBL_PURCHASE_ORDER, TBL_PURCHASE_ORDER_ITEM

def reset_db():
    print("Importing models...")
    for root, _, files in os.walk('api'):
        for file in files:
            if file == "models.py":
                module_path = os.path.relpath(root, '.').replace(os.path.sep, ".")
                module_name = f"{module_path}.models"
                try:
                    importlib.import_module(module_name)
                    print(f"Imported: {module_name}")
                except Exception as e:
                    print(f"Error importing {module_name}: {e}")

    print("Dropping all tables...")
    Base.metadata.drop_all(bind=engine)
    print("Creating all tables...")
    Base.metadata.create_all(bind=engine)
    print("Database reset successful.")

if __name__ == "__main__":
    reset_db()
