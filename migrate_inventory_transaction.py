from core.db import engine, Base
from api.inventory.models import TBL_INVENTORY_TRANSACTION
from api.books.models import TBL_BOOK

Base.metadata.create_all(bind=engine)
print("Tables created successfully.")
