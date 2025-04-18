import logging
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Form,
    Request, # Import Request
    BackgroundTasks # Import BackgroundTasks if needed for simple tasks
)
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List, Union

from app.database import get_db
from app.services.database_service import DatabaseService
from app.services.input_handler import InputHandler
from app.services.llm_service import LLMService # For triggering topic task
from app.schemas import job as job_schemas # Use alias to avoid name conflicts
from app.models.video_job import JobStatus # Import enum

logger = logging.getLogger(__name__)

# Define router
router = APIRouter()

# Instantiate services (dependency injection could be used later if needed)
# These could also be dependencies if they had state or complex setup
input_handler = InputHandler()
db_service = DatabaseService()
llm_service = LLMService() # Needed to access the task trigger


@router.post("/jobs",
             response_model=job_schemas.JobSubmissionResponse,
             status_code=status.HTTP_202_ACCEPTED, # 202 Accepted as tasks run in background
             summary="Submit a new video generation job")
async def create_new_job(
    source_type: str = Form(...),
    prompt_text: Optional[str] = Form(None),
    youtube_url: Optional[str] = Form(None),
    audio_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Creates a new video generation job based on the provided input type.

    - **source_type**: 'prompt', 'youtube_url', or 'audio_file'.
    - **prompt_text**: Required if source_type is 'prompt'.
    - **youtube_url**: Required if source_type is 'youtube_url'.
    - **audio_file**: Required if source_type is 'audio_file'.
    """
    logger.info(f"Received job creation request. Source type: {source_type}")

    source_value: Optional[Union[str, UploadFile]] = None
    if source_type == "prompt":
        if not prompt_text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="prompt_text is required for source_type 'prompt'")
        source_value = prompt_text
        logger.debug(f"Processing prompt: {prompt_text[:100]}...") # Log snippet
    elif source_type == "youtube_url":
        if not youtube_url:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="youtube_url is required for source_type 'youtube_url'")
        source_value = youtube_url
        logger.debug(f"Processing YouTube URL: {youtube_url}")
    elif source_type == "audio_file":
        if not audio_file:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="audio_file is required for source_type 'audio_file'")
        source_value = audio_file
        logger.debug(f"Processing uploaded file: {audio_file.filename}, content_type: {audio_file.content_type}")
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid source_type: {source_type}")

    try:
        # The input_handler saves the initial job record and triggers tasks
        job = await input_handler.process_new_job(db, source_type, source_value)
        # Note: db.commit() is handled by the get_db dependency on success,
        # or rolled back on exception within process_new_job or get_db.

        # We already committed the initial state in process_new_job
        # Let's return the ID and initial status
        return job_schemas.JobSubmissionResponse(
            job_id=job.id,
            status=job.status
        )

    except (ValueError, IOError) as e: # Catch specific errors from input handler
         logger.error(f"Input processing error: {e}", exc_info=True)
         # Rollback is handled by get_db dependency wrapper
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error creating job: {e}", exc_info=True)
        # Rollback handled by get_db
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error processing job request.")


@router.get("/jobs/{job_id}/status",
            response_model=job_schemas.JobStatusResponse,
            summary="Get the status and basic details of a job")
async def get_job_status(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieves the current status, status message, and potentially
    the transcript or topics if available for a given job ID.
    """
    logger.debug(f"Fetching status for job_id: {job_id}")
    job = await db_service.get_job(db, job_id)
    if not job:
        logger.warning(f"Job status request for non-existent job_id: {job_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found.")

    # Prepare topics list if available
    topics_list = job.topics if isinstance(job.topics, list) else None

    return job_schemas.JobStatusResponse(
        job_id=job.id,
        status=job.status,
        status_message=job.status_message,
        transcript=job.transcript if job.transcript_fetched else None, # Only show if fetched
        topics=topics_list
    )


@router.get("/jobs/{job_id}",
            response_model=job_schemas.Job, # Returns the full job details
            summary="Get full details of a specific job")
async def get_job_details(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Retrieves all details for a specific job ID.
    """
    logger.debug(f"Fetching full details for job_id: {job_id}")
    job = await db_service.get_job(db, job_id)
    if not job:
        logger.warning(f"Full details request for non-existent job_id: {job_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found.")

    # Pydantic's from_attributes will handle the conversion
    return job


@router.post("/jobs/{job_id}/generate_topics",
             response_model=job_schemas.JobStatusResponse, # Return current status after triggering
             status_code=status.HTTP_202_ACCEPTED,
             summary="Trigger topic generation for a job")
async def trigger_topic_generation(job_id: int, db: AsyncSession = Depends(get_db)):
    """
    Triggers the background task to generate topics for a job
    that has a completed transcript.
    """
    logger.info(f"Received request to generate topics for job_id: {job_id}")
    job = await db_service.get_job(db, job_id)
    if not job:
        logger.warning(f"Topic generation request for non-existent job_id: {job_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found.")

    # --- Validation checks ---
    if not job.transcript or not job.transcript_fetched:
         logger.warning(f"Attempted topic generation for job {job_id} without transcript.")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transcript is not ready for this job.")
    if job.status not in [JobStatus.COMPLETED, JobStatus.EDITING]: # Allow triggering if transcript is ready (COMPLETED after transcription)
        logger.warning(f"Attempted topic generation for job {job_id} with invalid status: {job.status.value}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot generate topics when job status is {job.status.value}. Transcript must be ready.")
    if job.topics is not None: # Check if topics already exist (simple check)
        logger.warning(f"Topics already exist for job {job_id}. Trigger request ignored.")
        # Return current status, indicating topics might already be there
        return job_schemas.JobStatusResponse(
            job_id=job.id, status=job.status, status_message="Topics have already been generated or generation was previously triggered.",
            transcript=job.transcript, topics=job.topics if isinstance(job.topics, list) else None
        )
        # Alternatively, raise 400 Bad Request
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Topics have already been generated for this job.")

    try:
        # Update status immediately to show topic generation is starting
        updated_job = await db_service.update_job_status(db, job_id, JobStatus.PROCESSING, "Topic generation initiated...")
        #await db.commit() # Commit this status update before triggering task

        # Trigger the background task
        LLMService.generate_topics_task.delay(job_id)
        logger.info(f"Topic generation task triggered for job_id: {job_id}")

        # Return the status reflecting that topic generation has started
        return job_schemas.JobStatusResponse(
             job_id=updated_job.id,
             status=updated_job.status,
             status_message=updated_job.status_message,
             transcript=updated_job.transcript, # Include transcript
             topics=None # Topics are not ready yet
         )

    except Exception as e:
        logger.error(f"Error triggering topic generation for job {job_id}: {e}", exc_info=True)
        # Rollback handled by get_db
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to trigger topic generation.")