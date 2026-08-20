import os
import importlib
from config import configs
from core.db import Base, engine
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError


def ensure_database_exists():
    """
    Connect to default 'postgres' database to ensure the target database exists.
    Creates the database automatically if it does not exist.
    """
    try:
        import psycopg2
        from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
        from psycopg2 import sql

        target_db = configs.POSTGRES_DB
        conn = psycopg2.connect(
            dbname="postgres",
            user=configs.POSTGRES_USER,
            password=configs.POSTGRES_PASSWORD,
            host=configs.POSTGRES_SERVER,
            port=configs.POSTGRES_PORT,
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (target_db,))
            exists = cur.fetchone()
            if not exists:
                print(f"Database '{target_db}' does not exist. Creating database...")
                cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target_db)))
                print(f"Database '{target_db}' created successfully.")
            else:
                print(f"Database '{target_db}' exists.")
        conn.close()
    except Exception as e:
        print(f"Note: Skipped auto-create database check: {e}")


def import_models(base_path: str, sub_path: str = "api"):
    """
    Dynamically import all models.py files from the api modules.
    """
    for root, _, files in os.walk(os.path.join(base_path, sub_path)):
        for file in files:
            if file == "models.py":
                module_path = os.path.relpath(root, base_path).replace(os.path.sep, ".")
                module_name = f"{module_path}.models"
                try:
                    importlib.import_module(module_name)
                    print(f"Imported: {module_name}")
                except ImportError as e:
                    print(f"Error importing {module_name}: {e}")


def create_tables():
    """
    Create all tables defined in the models.
    """
    # 1. Ensure target database exists
    ensure_database_exists()

    # 2. Import all models
    import_models(os.getcwd())

    # 3. Verify connection to the database
    try:
        with engine.connect() as connection:
            print("Database connection successful.")
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return

    # Check if tables are loaded in metadata
    if not Base.metadata.tables:
        print("No tables found to create.")
        return

    print(f"Tables registered in models ({len(Base.metadata.tables)}): {list(Base.metadata.tables.keys())}")

    # Inspect public schema before creation
    inspector_before = inspect(engine)
    tables_in_public_before = inspector_before.get_table_names(schema="public")
    print(f"Tables in public schema before creation: {len(tables_in_public_before)}")

    try:
        # Create all tables
        Base.metadata.create_all(bind=engine)
        print("All tables have been created successfully.")
    except SQLAlchemyError as e:
        print(f"Error creating tables: {e}")
        return

    # Fresh inspector to verify tables after creation
    inspector_after = inspect(engine)
    tables_in_public_after = inspector_after.get_table_names(schema="public")
    print(f"Tables in public schema after creation ({len(tables_in_public_after)}): {tables_in_public_after}")


if __name__ == "__main__":
    create_tables()

