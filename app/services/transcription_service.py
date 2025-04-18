import logging
import os
import tempfile
from pathlib import Path
from openai import AsyncOpenAI # Use Async client

from app.celery_app import celery
from app.core.config import settings
from app.services.database_service import DatabaseService # Import service class
from app.models.video_job import JobStatus # Import enum
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal # Import session factory for task

logger = logging.getLogger(__name__)

# Initialize OpenAI client (consider doing this once globally if possible)
# Ensure API key is loaded via settings
if not settings.OPENAI_API_KEY:
    logger.warning("OPENAI_API_KEY not found in settings. Transcription will fail.")
    # raise ValueError("OPENAI_API_KEY must be configured") # Or handle gracefully
    client = None
else:
    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


class TranscriptionService:
    """Handles audio transcription using OpenAI Whisper."""

    @staticmethod
    @celery.task(name="tasks.transcribe_audio", bind=True) # Use bind=True to access task instance
    async def transcribe_audio_task(self, job_id: int, audio_file_path_str: str):
        """
        Celery task to transcribe audio file using Whisper API.
        Updates job status and stores transcript in DB.
        """
        logger.info(f"Starting transcription task for job_id: {job_id}")
        db_service = DatabaseService() # Instantiate service inside task
        audio_file_path = Path(audio_file_path_str)
        transcript_text = None
        final_status = JobStatus.FAILED
        status_message = "Transcription failed"

        # Use AsyncSessionLocal for database operations within the async task
        async with AsyncSessionLocal() as db:
            try:
                # 1. Update Job Status to PROCESSING
                await db_service.update_job_status(db, job_id, JobStatus.PROCESSING, "Starting transcription...")
                await db.commit() # Commit status update

                if not client:
                     raise ValueError("OpenAI client not initialized. Check API Key.")

                if not audio_file_path.is_file():
                    raise FileNotFoundError(f"Audio file not found at path: {audio_file_path}")

                logger.info(f"Transcribing file: {audio_file_path} for job {job_id}")

                # 2. Call Whisper API
                # OpenAI library handles reading the file in chunks
                async with await client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file_path, # Pass Path object directly
                    response_format="text" # Get plain text transcript
                ) as response:
                     # The response object itself might be the string in v1+ library when format is 'text'
                     # Need to confirm exact handling with latest openai package version
                     # Assuming response directly contains the text here
                     if isinstance(response, str):
                         transcript_text = response
                     else:
                         # Handle potential future structured responses if format changes
                         # or if using 'json', 'verbose_json' etc.
                         logger.warning(f"Unexpected Whisper response type: {type(response)}")
                         # Attempt to extract text if possible, adjust based on actual response structure
                         transcript_text = str(response) # Fallback

                if transcript_text:
                    logger.info(f"Transcription successful for job {job_id}. Transcript length: {len(transcript_text)}")
                    final_status = JobStatus.COMPLETED # Mark as COMPLETED (ready for next step)
                    status_message = "Transcription successful. Ready for topic generation."
                else:
                    logger.error(f"Transcription failed for job {job_id} - empty response received.")
                    status_message = "Transcription failed: Empty response from API."


            except FileNotFoundError as e:
                logger.error(f"Transcription Error (Job {job_id}): {e}", exc_info=True)
                status_message = f"Transcription failed: {e}"
            except Exception as e:
                logger.error(f"Transcription Error (Job {job_id}): {e}", exc_info=True)
                # Check for specific API errors if needed
                status_message = f"Transcription failed: {e}"
                final_status = JobStatus.FAILED
                # Ensure db session rollbacks on general error if commit wasn't reached
                await db.rollback()

            finally:
                # 3. Update Job Status and Store Transcript/Error
                try:
                    update_data = {
                        "status": final_status,
                        "status_message": status_message,
                        "transcript": transcript_text,
                        "transcript_fetched": True # Mark transcript step as attempted/done
                    }
                    await db_service.update_job(db, job_id, update_data)
                    await db.commit() # Commit final status and transcript/error
                    logger.info(f"Final status for job {job_id}: {final_status.value}")
                except Exception as db_err:
                     logger.error(f"Failed to update final job status for job {job_id}: {db_err}", exc_info=True)
                     await db.rollback() # Rollback if final update fails


                # 4. Clean up the downloaded/uploaded audio file
                try:
                    if audio_file_path.is_file():
                        os.remove(audio_file_path)
                        logger.info(f"Cleaned up temporary audio file: {audio_file_path}")
                except OSError as e:
                    logger.error(f"Error cleaning up audio file {audio_file_path}: {e}", exc_info=True)

        return {"job_id": job_id, "status": final_status.value, "transcript_length": len(transcript_text or "")}

    # Optional: Add a synchronous wrapper if needed elsewhere, though async task preferred
    # async def transcribe_audio(self, audio_path: Path) -> str:
    #     # This would call the API directly, not as a task
    #     pass