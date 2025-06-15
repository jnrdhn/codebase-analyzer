# app/models.py
import enum
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

# This would be configured more robustly in a real app
# DATABASE_URL = "postgresql://user:password@localhost/dbname" # Or "sqlite:///./test.db"
DATABASE_URL = "sqlite:///./jobs.db"
engine = create_engine(
    DATABASE_URL, connect_args={"check_same_thread": False}
)
Base = declarative_base()

class JobStatus(str, enum.Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    github_url = Column(String, index=True)
    status = Column(Enum(JobStatus), default=JobStatus.PENDING)
    report_content = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

# This line creates the table in your database if it doesn't exist.
# You'd typically run this once or use a migration tool like Alembic.
Base.metadata.create_all(bind=engine)