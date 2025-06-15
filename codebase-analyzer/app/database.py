# app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# We'll use the same DATABASE_URL from our models file.
# Using SQLite for simplicity.
DATABASE_URL = "sqlite:///./jobs.db"

engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get a DB session
def get_db():
    """
    A FastAPI dependency that creates and yields a new database session
    for each request, and ensures it's closed afterwards.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()