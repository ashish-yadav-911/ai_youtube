# import logging
# from celery import Celery
# from app.core.config import settings
# from app.core.logging_config import setup_logging # Import setup function

# # Ensure logging is configured when Celery starts
# setup_logging()
# log = logging.getLogger(__name__)
# log.info("Configuring Celery application...")

# celery = Celery(
#     "yt_auto_vid_suite",
#     broker=settings.CELERY_BROKER_URL,
#     backend=settings.CELERY_RESULT_BACKEND,
#     include=[ # List of modules where tasks are defined
#         # Add paths to task modules here later, e.g.:
#         'app.services.transcription_service',
#         'app.services.video_generator',
#         'app.services.youtube_service',
#         'app.services.llm_service', # If topic gen is a task
#         'app.services.media_fetcher', # If media fetching is long
#     ],
# )

# # Optional Celery configuration
# celery.conf.update(
#     task_serializer="json", # Use json for task serialization
#     accept_content=["json"], # Accept json content
#     result_serializer="json", # Use json for results
#     timezone="UTC", # Use UTC timezone
#     enable_utc=True,
#     # Add other configurations as needed
#     # E.g., task routing, rate limits
#     worker_prefetch_multiplier=1, # Important for long-running tasks like video rendering
#     task_acks_late=True, # Acknowledge task only after completion (or failure)
# )

# log.info(f"Celery configured with broker: {settings.CELERY_BROKER_URL}")
# log.info(f"Celery result backend: {settings.CELERY_RESULT_BACKEND}")
# log.info(f"Celery including tasks from: {celery.conf.include}")

# # Example of how to define a task (will be moved to service files later)
# # @celery.task
# # def add(x, y):
# #     return x + y

import logging
from celery import Celery
from app.core.config import settings
from app.core.logging_config import setup_logging # Import setup function

# Ensure logging is configured when Celery starts
setup_logging()
log = logging.getLogger(__name__)
log.info("Configuring Celery application...")

celery = Celery(
    # Use project name from settings if desired, or keep specific name
    settings.PROJECT_NAME or "yt_auto_vid_suite",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[ # List of modules where tasks are defined
        # Add paths to task modules here
        'app.services.transcription_service', # Contains transcribe_audio_task
        'app.services.input_handler',      # Contains download_youtube_audio_task
        'app.services.llm_service',          # Contains generate_topics_task
        # Add future tasks here:
        # 'app.services.video_generator',
        # 'app.services.youtube_service',
        # 'app.services.media_fetcher',
    ],
)

# Optional Celery configuration (keep as before)
celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    # Optional: Set default task routing, rate limits etc.
    # task_routes = {'tasks.transcribe_audio': {'queue': 'transcription'},} # Example routing
)

log.info(f"Celery configured with broker: {settings.CELERY_BROKER_URL}")
log.info(f"Celery result backend: {settings.CELERY_RESULT_BACKEND}")
log.info(f"Celery including tasks from: {celery.conf.include}")