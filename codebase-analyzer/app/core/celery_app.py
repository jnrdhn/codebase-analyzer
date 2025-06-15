# app/core/celery_app.py
from celery import Celery

# Create a Celery instance
# The first argument 'tasks' is the name of the module where tasks are defined.
# The 'broker' argument specifies the URL of our message broker (Redis).
# 'backend' is used to store results, which is also good practice.
celery = Celery(
    "tasks",
    broker="redis://localhost:6379/0",
    backend="redis://localhost:6379/0",
    include=["app.tasks"]
)

# Optional configuration
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)