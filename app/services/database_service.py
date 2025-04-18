# import logging
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select # Use future select for 2.0 style
# from sqlalchemy import update # Import update statement
# from typing import Optional, List, Dict, Any

# from app.models.video_job import VideoJob, JobStatus
# from app.schemas.job import JobCreate # Import schema if needed for creation logic

# logger = logging.getLogger(__name__)

# class DatabaseService:
#     """Handles database operations for VideoJob."""

#     async def create_job(self, db: AsyncSession, source_type: str, source_value: str) -> VideoJob:
#         """Creates a new VideoJob record in the database."""
#         try:
#             new_job = VideoJob(
#                 source_type=source_type,
#                 source_value=source_value,
#                 status=JobStatus.PENDING, # Initial status
#                 status_message="Job submitted. Waiting for processing..."
#             )
#             db.add(new_job)
#             await db.flush() # Assigns ID without full commit yet
#             await db.refresh(new_job)
#             logger.info(f"Created new VideoJob with ID: {new_job.id}")
#             return new_job
#         except Exception as e:
#             logger.error(f"Error creating VideoJob: {e}", exc_info=True)
#             await db.rollback() # Rollback on error during creation
#             raise

#     async def get_job(self, db: AsyncSession, job_id: int) -> Optional[VideoJob]:
#         """Retrieves a VideoJob by its ID."""
#         try:
#             result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
#             job = result.scalar_one_or_none()
#             if job:
#                 logger.debug(f"Retrieved VideoJob with ID: {job_id}")
#             else:
#                 logger.warning(f"VideoJob with ID: {job_id} not found.")
#             return job
#         except Exception as e:
#             logger.error(f"Error retrieving job {job_id}: {e}", exc_info=True)
#             return None # Or re-raise depending on desired handling

#     async def update_job_status(self, db: AsyncSession, job_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[VideoJob]:
#         """Updates the status and optional message of a VideoJob."""
#         return await self._update_job(db, job_id, {"status": status, "status_message": message})

#     async def update_job(self, db: AsyncSession, job_id: int, update_data: Dict[str, Any]) -> Optional[VideoJob]:
#         """Updates arbitrary fields of a VideoJob."""
#         return await self._update_job(db, job_id, update_data)

#     async def _update_job(self, db: AsyncSession, job_id: int, update_data: Dict[str, Any]) -> Optional[VideoJob]:
#         """Internal helper to update VideoJob fields."""
#         # Filter out None values from update_data unless explicitly allowed for a field
#         filtered_data = {k: v for k, v in update_data.items() if v is not None}
#         if not filtered_data:
#             logger.warning(f"No fields provided to update for job {job_id}.")
#             return await self.get_job(db, job_id) # Return current job data

#         try:
#             # Use the update statement for efficiency
#             stmt = (
#                 update(VideoJob)
#                 .where(VideoJob.id == job_id)
#                 .values(**filtered_data)
#                 .returning(VideoJob) # Return the updated row data
#             )
#             result = await db.execute(stmt)
#             # await db.flush() # Flush to ensure changes are sent, commit handled by context/dependency

#             updated_job = result.scalar_one_or_none() # Fetch the result of returning()

#             if updated_job:
#                  logger.info(f"Updated VideoJob {job_id} with data: {filtered_data}")
#                  # Refresh might be needed if relationships are involved or complex defaults
#                  # await db.refresh(updated_job) # Not strictly needed here for simple fields
#                  return updated_job
#             else:
#                  logger.warning(f"Attempted to update non-existent job ID: {job_id}")
#                  return None

#         except Exception as e:
#             logger.error(f"Error updating job {job_id}: {e}", exc_info=True)
#             # Rollback might be handled by the request context, but doesn't hurt here
#             # await db.rollback() # Rollback might be handled by get_db dependency
#             raise # Re-raise the exception to be caught by FastAPI handler

# # Optional: Instantiate if you prefer using an instance
# # db_service = DatabaseService()

import logging
from sqlalchemy.ext.asyncio import AsyncSession
# --- Import Sync Session ---
from sqlalchemy.orm import Session as SyncSession
from sqlalchemy.future import select
from sqlalchemy import update, inspect # Import inspect
from typing import Optional, List, Dict, Any

from app.models.video_job import VideoJob, JobStatus
from app.schemas.job import JobCreate

logger = logging.getLogger(__name__)

class DatabaseService:
    """Handles database operations for VideoJob. Includes async and sync methods."""

    # === ASYNC Methods (for FastAPI) ===

    # async def create_job(self, db: AsyncSession, source_type: str, source_value: str) -> VideoJob:
    #     # ... (keep existing async implementation) ...
    #     try:
    #         new_job = VideoJob(...)
    #         db.add(new_job)
    #         await db.flush()
    #         await db.refresh(new_job)
    #         logger.info(f"ASYNC: Created new VideoJob with ID: {new_job.id}")
    #         return new_job
    #     except Exception as e:
    #         logger.error(f"ASYNC Error creating VideoJob: {e}", exc_info=True)
    #         await db.rollback()
    #         raise
        # === ASYNC Methods (for FastAPI) ===

    async def create_job(self, db: AsyncSession, source_type: str, source_value: str) -> VideoJob:
        # ... (keep existing async implementation) ... # <--- THIS COMMENT IS MISLEADING
        try:
            # THIS LINE IS LIKELY THE PROBLEM IF IT WASN'T UPDATED
            new_job = VideoJob(
                source_type=source_type,
                source_value=source_value,
                status=JobStatus.PENDING,
                status_message="Job submitted. Waiting for processing..."
            )
            db.add(new_job)
            await db.flush()
            await db.refresh(new_job)
            logger.info(f"ASYNC: Created new VideoJob with ID: {new_job.id}")
            return new_job
        except Exception as e:
            logger.error(f"ASYNC Error creating VideoJob: {e}", exc_info=True)
            await db.rollback()
            raise

    async def get_job(self, db: AsyncSession, job_id: int) -> Optional[VideoJob]:
        # ... (keep existing async implementation) ...
        try:
            result = await db.execute(select(VideoJob).where(VideoJob.id == job_id))
            job = result.scalar_one_or_none()
            # ... logging ...
            return job
        except Exception as e:
            # ... error logging ...
            return None

    async def update_job_status(self, db: AsyncSession, job_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[VideoJob]:
        return await self._update_job_async(db, job_id, {"status": status, "status_message": message})

    async def update_job(self, db: AsyncSession, job_id: int, update_data: Dict[str, Any]) -> Optional[VideoJob]:
        return await self._update_job_async(db, job_id, update_data)

    async def _update_job_async(self, db: AsyncSession, job_id: int, update_data: Dict[str, Any]) -> Optional[VideoJob]:
        # ... (keep existing async implementation) ...
        filtered_data = {k: v for k, v in update_data.items() if v is not None or k in ['topics','script_genre']} # Allow setting back to None for these
        if not filtered_data: # Handle empty update
            logger.warning(f"ASYNC: No fields provided to update for job {job_id}.")
            # Check if job exists before trying to return it
            existing_job = await self.get_job(db, job_id)
            return existing_job

        try:
            stmt = update(VideoJob).where(VideoJob.id == job_id).values(**filtered_data).returning(VideoJob)
            result = await db.execute(stmt)
            updated_job = result.scalar_one_or_none()
            if updated_job:
                 logger.info(f"ASYNC: Updated VideoJob {job_id} with data: {filtered_data}")
                 return updated_job
            else:
                 logger.warning(f"ASYNC: Attempted to update non-existent job ID: {job_id}")
                 return None
        except Exception as e:
            logger.error(f"ASYNC Error updating job {job_id}: {e}", exc_info=True)
            raise

    # === SYNC Methods (for Celery) ===

    def get_job_sync(self, db: SyncSession, job_id: int) -> Optional[VideoJob]:
        """Retrieves a VideoJob by its ID synchronously."""
        try:
            # Use Session.get() for primary key lookup if preferred, or select
            # job = db.get(VideoJob, job_id) # Simpler way for primary key
            job = db.execute(select(VideoJob).where(VideoJob.id == job_id)).scalar_one_or_none()
            if job:
                logger.debug(f"SYNC: Retrieved VideoJob with ID: {job_id}")
            else:
                logger.warning(f"SYNC: VideoJob with ID: {job_id} not found.")
            return job
        except Exception as e:
            logger.error(f"SYNC Error retrieving job {job_id}: {e}", exc_info=True)
            return None

    def update_job_status_sync(self, db: SyncSession, job_id: int, status: JobStatus, message: Optional[str] = None) -> Optional[VideoJob]:
        """Updates the status and optional message of a VideoJob synchronously."""
        return self._update_job_sync(db, job_id, {"status": status, "status_message": message})

    def _update_job_sync(self, db: SyncSession, job_id: int, update_data: Dict[str, Any]) -> Optional[VideoJob]:
        """Internal helper to update VideoJob fields synchronously."""
        filtered_data = {k: v for k, v in update_data.items() if v is not None or k in ['topics','script_genre']}
        if not filtered_data:
            logger.warning(f"SYNC: No fields provided to update for job {job_id}.")
            return self.get_job_sync(db, job_id)

        try:
            # Fetch the object first for sync update (alternative to update().returning())
            job = self.get_job_sync(db, job_id)
            if not job:
                 logger.warning(f"SYNC: Attempted to update non-existent job ID: {job_id}")
                 return None

            # Update attributes directly
            for key, value in filtered_data.items():
                 setattr(job, key, value)

            db.add(job) # Add to session to mark dirty
            db.flush() # Persist changes
            db.refresh(job) # Refresh object state

            logger.info(f"SYNC: Updated VideoJob {job_id} with data: {filtered_data}")
            return job

        except Exception as e:
            logger.error(f"SYNC Error updating job {job_id}: {e}", exc_info=True)
            db.rollback() # Rollback on error
            raise