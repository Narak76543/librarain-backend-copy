from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import configs
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine = create_engine(
    configs.DATABASE_URL, 
    pool_timeout=30, 
    pool_pre_ping=True
)

Session = sessionmaker(bind=engine)
def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()