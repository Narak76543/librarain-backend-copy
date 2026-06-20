import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import UUID, INET

@compiles(UUID, 'sqlite')
def compile_uuid(element, compiler, **kw):
    return "VARCHAR(36)"

@compiles(INET, 'sqlite')
def compile_inet(element, compiler, **kw):
    return "VARCHAR(45)"

from main import app
from core.db import Base, get_db

# Use an in-memory SQLite database for tests
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    # Create tables
    Base.metadata.create_all(bind=engine)
    yield
    # Drop tables after tests finish
    Base.metadata.drop_all(bind=engine)

@pytest.fixture(scope="function")
def db():
    # Provide a transaction per test so we can roll it back
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()

@pytest.fixture(scope="function")
def client(db):
    # Override get_db dependency
    def override_get_db():
        try:
            yield db
        finally:
            pass
            
    app.dependency_overrides[get_db] = override_get_db
    
    # Mocking external calls to prevent test failures or side effects
    from api.auth_user import views as auth_views
    import api.books.views as books_views
    
    # Simple mock functions
    async def mock_send_email(*args, **kwargs):
        pass
        
    def mock_upload_cover(*args, **kwargs):
        return "https://res.cloudinary.com/demo/image/upload/sample.jpg"
        
    # Apply mocks if possible
    if hasattr(auth_views, "send_otp_email"):
        auth_views.send_otp_email = mock_send_email
        
    if hasattr(books_views, "upload_cover_to_cloudinary"):
        books_views.upload_cover_to_cloudinary = mock_upload_cover
    
    with TestClient(app) as c:
        yield c
        
    app.dependency_overrides.clear()
