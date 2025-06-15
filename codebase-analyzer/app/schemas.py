# app/schemas.py
from pydantic import BaseModel
from datetime import datetime
from .models import JobStatus

class JobBase(BaseModel):
    github_url: str

class JobCreate(JobBase):
    pass

class Job(JobBase):
    id: int
    status: JobStatus
    created_at: datetime
    report_content: str | None = None

    class Config:
        orm_mode = True # Allows Pydantic to read data from ORM models