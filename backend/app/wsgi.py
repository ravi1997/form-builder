import os
from app import create_app
from app.workers.analysis_tasks import celery_app as celery

env = os.environ.get("FLASK_ENV", "development")
app = create_app(env)
