from sqlalchemy import create_engine, text
from core.db import SQLALCHEMY_DATABASE_URL

engine = create_engine(SQLALCHEMY_DATABASE_URL)
with engine.connect() as conn:
    # Kill all other connections to clear locks
    conn.execute(text("""
    SELECT pg_terminate_backend(pid)
    FROM pg_stat_activity
    WHERE pid <> pg_backend_pid()
    AND state in ('idle in transaction', 'active')
    AND datname = current_database();
    """))
    conn.commit()
    print("Killed hanging transactions.")
