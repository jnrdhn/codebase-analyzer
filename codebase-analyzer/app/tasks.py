# app/tasks.py
import os
import subprocess
import tempfile
from google import genai
from google.genai import types
from sqlalchemy.orm import sessionmaker

from .core.celery_app import celery
from . import models, crud
from .models import engine, JobStatus

# --- Gemini Configuration & Helpers from Phase 1 ---
# Note: These are now helper functions within the tasks module.

AI_MODEL = "gemini-1.5-flash"
SUPPORTED_EXTENSIONS = { ".py", ".js", ".ts", ".go", ".java", ".sql", ".jsx" } # Simplified for example
TOP_K_FILES = 5
SYSTEM_INSTRUCTION = """
You are an expert software engineering assistant. Your task is to analyze individual source code files and provide a concise, high-level summary.

Your entire response MUST be in markdown format.
Do NOT wrap your response in a markdown code block (i.e., do not use ```markdown).
Structure your response with the following headers: '## Purpose', '## Key Components', and '## Potential Complexities'.
"""

# Configure Gemini once when the worker starts
try:
    client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
except Exception as e:
    print(f"Failed to configure Gemini: {e}")


def _clone_repo(repo_url, temp_dir):
    try:
        subprocess.run(["git", "clone", repo_url, temp_dir], check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise IOError(f"Failed to clone repo: {e.stderr}")

def _find_top_k_files(repo_path):
    file_paths = []
    for root, _, files in os.walk(repo_path):
        if '.git' in root: continue
        for file in files:
            if any(file.endswith(ext) for ext in SUPPORTED_EXTENSIONS):
                full_path = os.path.join(root, file)
                try:
                    file_paths.append((full_path, os.path.getsize(full_path)))
                except OSError: continue
    file_paths.sort(key=lambda x: x[1], reverse=True)
    return [path for path, size in file_paths[:TOP_K_FILES]]

def _get_code_summary_from_gemini(client, file_path, repo_path):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    if len(content) > 20000:
        content = content[:20000] + "\n... (file truncated)"
    
    user_prompt = f"Analyze this file: `{os.path.relpath(file_path, repo_path)}`\n\n```\n{content}\n```"
    response = client.models.generate_content(
            model='gemini-2.0-flash-001',
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION
            ),
        )
    # ---CLEANUP LOGIC ---
    cleaned_text = response.text
    if cleaned_text.startswith("```markdown"):
        cleaned_text = cleaned_text.strip() # Remove leading/trailing whitespace
        # Split the string by the code fence, take the content, and clean it up
        parts = cleaned_text.split("```markdown", 1)
        if len(parts) > 1:
            cleaned_text = parts[1]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3].strip()
    return response.text

# --- The Celery Task ---
# This is the function that will be executed by our worker.

@celery.task
def analyze_repository_task(job_id: int):
    """
    The main Celery task to perform repository analysis.
    It's decorated with @celery.task to register it with Celery.
    """
    # Each task needs its own database session.
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    try:
        # 1. Fetch the job details from the database
        job = crud.get_job(db, job_id)
        if not job:
            return f"Job with ID {job_id} not found."
        
        # 2. Update status to RUNNING to provide user feedback
        crud.update_job_status_and_report(db, job_id, status=JobStatus.RUNNING)
        
        # 3. Perform the analysis (your core logic)
        with tempfile.TemporaryDirectory() as temp_dir:
            _clone_repo(job.github_url, temp_dir)
            files_to_analyze = _find_top_k_files(temp_dir)
            
            if not files_to_analyze:
                raise ValueError("No supported files found in the repository.")

            markdown_report = f"# AI Analysis for `{job.github_url}`\n\n"
            for i, file_path in enumerate(files_to_analyze):
                relative_path = os.path.relpath(file_path, temp_dir)
                print(f"Worker analyzing [{i+1}/{len(files_to_analyze)}]: {relative_path}")
                summary = _get_code_summary_from_gemini(client, file_path, temp_dir)
                markdown_report += f"## Analysis of `{relative_path}`\n\n{summary}\n\n---\n\n"

        # 4. If successful, update status to COMPLETE and save the report
        crud.update_job_status_and_report(db, job_id, status=JobStatus.COMPLETE, report=markdown_report)
        print(f"Job {job_id} completed successfully.")

    except Exception as e:
        # 5. If any error occurs, update status to FAILED and record the error
        error_message = f"An error occurred: {str(e)}"
        crud.update_job_status_and_report(db, job_id, status=JobStatus.FAILED, report=error_message)
        print(f"Job {job_id} failed: {error_message}")
    finally:
        # 6. Always close the database session
        db.close()