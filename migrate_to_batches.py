import sys
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import configs
from api.books.models import TBL_BOOK
from api.inventory.models import TBL_STOCK_BATCH

def migrate():
    engine = create_engine(configs.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # 1. Create batches for existing stock
        books = session.query(TBL_BOOK).filter(TBL_BOOK.stock > 0).all()
        created_batches = 0
        
        print(f"Found {len(books)} books with stock > 0. Migrating to batches...")

        for book in books:
            # Check if a batch already exists to prevent duplicates on rerun
            existing_batch = session.query(TBL_STOCK_BATCH).filter(TBL_STOCK_BATCH.book_id == book.id).first()
            if existing_batch:
                print(f"Batch already exists for book {book.id}, skipping.")
                continue

            # Create a new legacy batch
            batch = TBL_STOCK_BATCH(
                book_id=book.id,
                supplier_id=None,  # Legacy stock has no known supplier
                po_item_id=None,
                initial_quantity=book.stock,
                remaining_quantity=book.stock,
                unit_cost_price=book.cost_price,
                status="active"
            )
            session.add(batch)
            created_batches += 1

        session.commit()
        print(f"Migration completed successfully. Created {created_batches} batches.")

    except Exception as e:
        session.rollback()
        print(f"Error during migration: {e}")
        raise e
    finally:
        session.close()

if __name__ == "__main__":
    print("Starting migration to inventory batches...")
    migrate()
