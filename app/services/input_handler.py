import logging
import os
from sqlalchemy import text

import uuid # For generating unique filenames
from pathlib import Path
import yt_dlp # For downloading YouTube audio
from fastapi import UploadFile
from typing import Optional, Union # Add Union here
from app.celery_app import celery
from app.core.config import settings
from app.services.database_service import DatabaseService
from app.services.transcription_service import TranscriptionService # Import the service
from app.models.video_job import JobStatus
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import AsyncSessionLocal # For tasks
from app.models.video_job import JobStatus, VideoJob # Add VideoJob here

logger = logging.getLogger(__name__)

class InputHandler:
    """Handles processing of different input types (prompt, URL, audio file)."""

    def __init__(self):
        self.db_service = DatabaseService()
        # Ensure download directory exists (should be done by config loader, but double check)
        settings.DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    async def process_new_job(self, db: AsyncSession, source_type: str, source_value: Union[str, UploadFile]) -> VideoJob:
        """
        Main entry point to process a new job request.
        Creates the initial job record and triggers background tasks if needed.
        """
        job = None # Initialize job to None
        try:
            if source_type == "prompt":
                # Prompt is handled directly, no file processing needed yet
                prompt_text = source_value if isinstance(source_value, str) else await source_value.read()
                if isinstance(prompt_text, bytes): # Decode if needed (though should be str)
                     prompt_text = prompt_text.decode('utf-8')

                job = await self.db_service.create_job(db, source_type, prompt_text)

                # Update status: Transcript is effectively 'fetched' (it's the prompt itself)
                # Mark as COMPLETED to allow topic generation right away for prompts
                await self.db_service.update_job(db, job.id, {
                    "transcript": prompt_text,
                    "transcript_fetched": True,
                    "status": JobStatus.COMPLETED, # Ready for next step (topics)
                    "status_message": "Prompt processed. Ready for topic generation."
                 })
                #await db.commit() # Commit changes for prompt job
                logger.info(f"Processed prompt directly for job {job.id}")
                return await self.db_service.get_job(db, job.id) # Return the updated job

            elif source_type == "youtube_url":
                if not isinstance(source_value, str):
                    raise ValueError("YouTube URL source value must be a string.")
                job = await self.db_service.create_job(db, source_type, source_value)
                await db.commit() # Commit the initial job creation
                logger.info(f"Created job {job.id} for YouTube URL. Triggering download task.")
                # Trigger Celery task for download and subsequent transcription
                self.download_youtube_audio_task.delay(job.id, source_value)
                # Status remains PENDING until download task updates it

            elif source_type == "audio_file":
                if not isinstance(source_value, UploadFile):
                     raise ValueError("Audio file source value must be an UploadFile.")
                # Save the uploaded file first
                original_filename = source_value.filename or "uploaded_audio"
                # Create a unique filename to avoid conflicts
                file_ext = Path(original_filename).suffix or ".tmp"
                unique_filename = f"{uuid.uuid4()}{file_ext}"
                audio_file_path = settings.DOWNLOAD_DIR / unique_filename

                try:
                    with open(audio_file_path, "wb") as buffer:
                        # Read chunk by chunk to handle large files
                        while content := await source_value.read(1024 * 1024): # Read 1MB chunks
                            buffer.write(content)
                    logger.info(f"Saved uploaded audio file to: {audio_file_path}")
                except Exception as e:
                    logger.error(f"Failed to save uploaded file {original_filename}: {e}", exc_info=True)
                    # Create job with error status? Or raise error? Let's raise for now.
                    raise IOError(f"Failed to save uploaded file: {e}")
                finally:
                    await source_value.close() # Close the upload file stream


                # Create job record after successful file save
                job = await self.db_service.create_job(db, source_type, str(audio_file_path)) # Store path as source_value
                await db.commit() # Commit initial job creation
                logger.info(f"Created job {job.id} for uploaded audio file. Triggering transcription task.")

                # Trigger Celery task for transcription directly
                TranscriptionService.transcribe_audio_task.delay(job.id, str(audio_file_path))
                # Status remains PENDING until transcription task updates it

            else:
                raise ValueError(f"Unsupported source type: {source_type}")

            if not job:
                 # This case should ideally not be reached if logic is correct
                 raise RuntimeError("Job object was not created successfully.")

            return job # Return the initially created job (status might update later via task)

        except Exception as e:
            logger.error(f"Error processing new job input: {e}", exc_info=True)
            # If job was created before error, update its status to FAILED
            if job and job.id:
                async with AsyncSessionLocal() as task_db: # Use separate session for potential update
                     try:
                         await self.db_service.update_job_status(task_db, job.id, JobStatus.FAILED, f"Input processing error: {e}")
                         await task_db.commit()
                     except Exception as db_err:
                         logger.error(f"Failed to update job {job.id} status to FAILED after input error: {db_err}", exc_info=True)
                         await task_db.rollback()
            raise # Re-raise the exception to be caught by the router


    @staticmethod
    @celery.task(name="tasks.download_youtube_audio", bind=True)
    async def download_youtube_audio_task(self, job_id: int, youtube_url: str):
        """
        Celery task to download audio from YouTube URL using yt-dlp.
        Triggers transcription task upon successful download.
        """
        logger.info(f"Starting YouTube download task for job_id: {job_id}, URL: {youtube_url}")
        db_service = DatabaseService() # Instantiate service inside task
        download_path = None
        final_status = JobStatus.FAILED
        status_message = "YouTube download failed"
        trigger_transcription = False

        # Use AsyncSessionLocal for database operations within the async task
        async with AsyncSessionLocal() as db:
            try:
                # 1. Update Job Status to PROCESSING
                await db_service.update_job_status(db, job_id, JobStatus.PROCESSING, f"Downloading audio from {youtube_url}...")
                await db.commit() # Commit status update

                # 2. Setup yt-dlp options
                # Create a unique filename for the download
                unique_filename_base = f"youtube_{job_id}_{uuid.uuid4()}"
                output_template = str(settings.DOWNLOAD_DIR / f"{unique_filename_base}.%(ext)s")

                ydl_opts = {
                    'format': 'bestaudio/best', # Download best audio quality
                    'outtmpl': output_template, # Output path template
                    'noplaylist': True, # Don't download playlists if URL points to one
                    'postprocessors': [{
                        'key': 'FFmpegExtractAudio', # Extract audio
                        'preferredcodec': 'mp3', # Convert to mp3 (Whisper prefers this)
                        'preferredquality': '192', # Audio quality
                    }],
                    'logger': logging.getLogger('yt_dlp'), # Integrate with our logging
                    'progress_hooks': [lambda d: InputHandler._yt_dlp_hook(d, job_id)], # Optional progress hook
                    # Consider adding limits: max_filesize, download_timeout etc.
                }

                logger.info(f"yt-dlp options for job {job_id}: {ydl_opts}")

                # 3. Run yt-dlp download (synchronous library, run in threadpool)
                # yt-dlp doesn't have a native async API, so we run it in Celery's thread pool
                # or use asyncio.to_thread if not in Celery context. Celery handles this.
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    # The actual download happens here. This can block.
                    ydl.download([youtube_url])

                # After download, figure out the exact output filename
                # The output template might result in .mp3 or other audio extension
                # Let's find the file based on the unique base name
                possible_extensions = ['.mp3', '.m4a', '.wav', '.ogg'] # Add more if needed
                downloaded_file = None
                for ext in possible_extensions:
                    potential_path = settings.DOWNLOAD_DIR / f"{unique_filename_base}{ext}"
                    if potential_path.is_file():
                        downloaded_file = potential_path
                        break

                if downloaded_file and downloaded_file.is_file():
                    download_path = str(downloaded_file)
                    logger.info(f"YouTube audio downloaded successfully for job {job_id} to: {download_path}")
                    # Don't change status yet, transcription will handle it
                    status_message = "Download successful. Starting transcription..."
                    trigger_transcription = True
                else:
                     logger.error(f"Download for job {job_id} completed, but output file not found with base: {unique_filename_base}")
                     status_message = "Download succeeded but output file not found."
                     final_status = JobStatus.FAILED


            except yt_dlp.utils.DownloadError as e:
                 logger.error(f"YouTube Download Error (Job {job_id}): {e}", exc_info=True)
                 status_message = f"YouTube download failed: {e}"
                 final_status = JobStatus.FAILED
                 await db.rollback() # Rollback DB if commit wasn't reached
            except Exception as e:
                logger.error(f"Generic Error during YouTube download (Job {job_id}): {e}", exc_info=True)
                status_message = f"YouTube download failed: {e}"
                final_status = JobStatus.FAILED
                await db.rollback() # Rollback DB if commit wasn't reached

            finally:
                # 4. Update status before triggering next task or setting final state
                try:
                    # Only update status if transcription isn't being triggered
                    # Otherwise, let the transcription task handle the next status update
                    if not trigger_transcription:
                        await db_service.update_job_status(db, job_id, final_status, status_message)
                        await db.commit()
                        logger.info(f"Final status for job {job_id} after download attempt: {final_status.value}")
                    else:
                         # Update status message to indicate transcription start
                         await db_service.update_job_status(db, job_id, JobStatus.PROCESSING, status_message)
                         await db.commit()

                except Exception as db_err:
                     logger.error(f"Failed to update job status for job {job_id} after download: {db_err}", exc_info=True)
                     await db.rollback()


        # 5. Trigger transcription task if download was successful
        if trigger_transcription and download_path:
            logger.info(f"Triggering transcription task for job {job_id} with file: {download_path}")
            TranscriptionService.transcribe_audio_task.delay(job_id, download_path)
        elif not trigger_transcription:
             logger.warning(f"Transcription not triggered for job {job_id} due to download failure.")


        return {"job_id": job_id, "status": final_status.value if not trigger_transcription else JobStatus.PROCESSING.value, "download_path": download_path}


    @staticmethod
    def _yt_dlp_hook(d, job_id):
        """Progress hook for yt-dlp."""
        if d['status'] == 'downloading':
            # Can log progress, but be careful not to flood logs
             total_bytes_est = d.get('total_bytes_estimate')
             downloaded_bytes = d.get('downloaded_bytes')
             speed = d.get('speed')
             eta = d.get('eta')
             if downloaded_bytes and total_bytes_est and speed and eta:
                 percent = (downloaded_bytes / total_bytes_est) * 100
                 # Log only every ~10% to avoid flooding? Or update DB? Be cautious.
                 if int(percent) % 10 == 0:
                      logger.debug(f"Job {job_id} Download Progress: {percent:.1f}% at {speed:.2f} B/s, ETA: {eta}s")
            # Potentially update DB status message with progress here, but adds overhead
            # db_service = DatabaseService()
            # async with AsyncSessionLocal() as db:
            #    await db_service.update_job_status(db, job_id, JobStatus.PROCESSING, f"Downloading: {percent:.1f}%")
            #    await db.commit() -> This adds many commits, maybe not ideal.

        elif d['status'] == 'finished':
            logger.info(f"yt-dlp finished downloading for job {job_id}. Filename: {d.get('filename')}")
        elif d['status'] == 'error':
            logger.error(f"yt-dlp reported an error for job {job_id}.")

