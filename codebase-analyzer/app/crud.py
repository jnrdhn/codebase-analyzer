# app/crud.py
from sqlalchemy.orm import Session
from . import models, schemas

def get_job(db: Session, job_id: int):
    """Retrieve a job from the database by its ID."""
    return db.query(models.Job).filter(models.Job.id == job_id).first()

def create_job(db: Session, job: schemas.JobCreate):
    """Create a new job record in the database."""
    db_job = models.Job(github_url=job.github_url, status=models.JobStatus.PENDING)
    db.add(db_job)
    db.commit()
    db.refresh(db_job)
    return db_job

def update_job_status_and_report(db: Session, job_id: int, status: models.JobStatus, report: str | None = None):
    """Update a job's status and optionally its report content."""
    db_job = get_job(db, job_id)
    if db_job:
        db_job.status = status
        if report:
            db_job.report_content = report
        db.commit()
        db.refresh(db_job)
    return db_job