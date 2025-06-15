# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from . import crud, models, schemas
from .database import engine, get_db
from .tasks import analyze_repository_task

# This line ensures the tables are created when the app starts.
# In a production app, you might use a migration tool like Alembic.
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Autonomous Codebase Analyst Agent",
    description="An API to analyze GitHub repositories using an AI agent.",
    version="1.0.0"
)

origins = [
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Which origins are allowed to make requests
    allow_credentials=True,      # Allow cookies
    allow_methods=["*"],         # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],         # Allow all headers
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serves the main index.html file."""
    with open("app/static/index.html") as f:
        return HTMLResponse(content=f.read(), status_code=200)

@app.post("/analyze/", response_model=schemas.Job, status_code=202)
def create_analysis_job(job_request: schemas.JobCreate, db: Session = Depends(get_db)):
    """
    Endpoint to submit a new GitHub repository for analysis.
    
    1. Creates a job record in the database.
    2. Dispatches the analysis task to the Celery worker.
    3. Returns the job details immediately. (Status code 202: Accepted)
    """
    # Create the initial job entry in the database.
    db_job = crud.create_job(db, job=job_request)
    
    # Send the task to the Celery worker.
    # .delay() is the shorthand to send a task to the queue.
    analyze_repository_task.delay(db_job.id)
    
    return db_job


@app.get("/jobs/{job_id}", response_model=schemas.Job)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """
    Endpoint to retrieve the status and results of an analysis job.
    
    Poll this endpoint after submitting a job to check its progress.
    """
    db_job = crud.get_job(db, job_id=job_id)
    if db_job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return db_job